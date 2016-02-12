#!/usr/bin/perl

my $input = q(EXTRAE_Paraver_trace_mpich); # input file name

use strict;
use warnings;
use Data::Dumper;
use Switch;

# use dictionary to keep track of states and events
my %states;
my %events;

# use dictionary to keep track of translated and ignored events
my %translated_events;
my %ignored_events;

my $number_of_tasks;

# store communicator id and size
my %communicators;

my @task_states_buffer;
my @task_events_buffer;
my @task_comms_buffer;

my $power_reference = 16.673; # in flop/µs taken from graphene simgrid platform

# store all tit events (complete or incomplete)
my @action_buffer;

# to define the root of collective operations (bcast, gather)
my %collective_root; # communicator(HASH), task(HASH), mpi_call(HASH) - ARRAY
my %collective_root_order; # communicator(HASH), mpi_call(HASH) - ARRAY

# to define recv/send counts of collective operations
my %v_counts;  # communicator(HASH), mpi_call(HASH) then one ARRAY (indicating order of operations) of ARRAYs (with the message sizes)
my %v_actions; # communicator(HASH), task(HASH), mpi_call(HASH), 

# to define the partner and comm size of ptp operations (send, recv, isend, irecv)
my %ptp_partner_comm; # task(HASH), "send" or "recv" - ARRAY
my @ptp_operations_order; # order on which PTP operations appear

sub check_undef_action
{
    my $action = @_;
    foreach my $value ($action){
        if (!defined $value){
            return undef;
        }
    }
    return 1;
}

sub dump_tit_lucas
{
    define_collective_root ();
    define_ptp_partner_comm_size ();
    define_v_fields ();
    
    foreach (@action_buffer){
        my $action = $_;
        my $type = $action->{"type"};
        my $task = $action->{"task"};
        $task = $task - 1; # remove one

        # check if action has no undefs
        if (!check_undef_action ($action)){
            die "action has undefs\n";
        }

        switch ($type){
            case ["compute"] {
                my $comp_size = $action->{"comp_size"};
                print "$task $type $comp_size\n";
            }

            case ["init", "finalize", "wait", "waitall", "barrier"] {
                # FORMAT: <rank> init [<set_default_double>]
                # FORMAT: <rank> finalize
                # FORMAT: <rank> wait
                # FORMAT: <rank> waitAll
                # FORMAT: <rank> barrier
                print "$task $type\n";
            }

            case ["bcast"] {
                # FORMAT: <rank> bcast <comm_size> [<root> [<datatype>]]
                my $comm_size = $action->{"comm_size"};
                my $root = $action->{"root"} - 1;
                print "$task $type $comm_size $root\n";
            }

            case ["gather"] {
                # FORMAT: <rank> gather <send_size> <recv_size> <root> [<send_datatype> <recv_datatype>]
                my $send_size = $action->{"send_size"};
                my $recv_size = $action->{"recv_size"};
                my $root = $action->{"root"} - 1;
                print "$task $type $send_size $recv_size $root\n";
            }

            case ["reduce"] {
                # FORMAT: <rank> reduce <comm_size> <comp_size> [<root> [<datatype>]]
                my $comm_size = $action->{"comm_size"};
                my $comp_size = $action->{"comp_size"};
                my $root = $action->{"root"} - 1;
                print "$task $type $comm_size $comp_size $root\n";
            }

            case ["allreduce"] {
                # FORMAT: <rank> allReduce <comm_size> <comp_size> [<datatype>]
                my $comm_size = $action->{"comm_size"};
                my $comp_size = $action->{"comp_size"};
                print "$task $type $comm_size $comp_size\n";
            }

            case ["send", "recv", "isend", "irecv"] {
                # FORMAT: <rank> send <dst> <comm_size> [<datatype>]
                my $partner = $action->{"partner"} - 1;
                my $comm_size = $action->{"comm_size"};
                print "$task $type $partner $comm_size\n";
            }

            case ["allgather", "alltoall"] {
                # FORMAT: <rank> allGather <send_size> <recv_size> [<send_datatype> <recv_datatype>]
                # FORMAT: <rank> allToAll <send_size> <recv_recv> [<send_datatype> <recv_datatype>]
                my $send_size = $action->{"send_size"};
                my $recv_size = $action->{"recv_size"};
                print "$task $type $send_size $recv_size\n";
            }

            case ["gatherv"] {
                # FORMAT: <rank> gatherV <send_size> <recv_sizes†> <root> [<send_datatype> <recv_datatype>]
                my $send_size = $action->{"send_size"};
                my $recv_sizes = join(" ", @{$action->{"recv_sizes"}});
                my $root =  $action->{"root"} - 1;
                print "$task $type $send_size $recv_sizes $root\n";
            }

            case ["allgatherv"] {
                # FORMAT: <rank> allGatherV <send_size> <recv_sizes†> [<send_datatype> <recv_datatype>]
                my $send_size = $action->{"send_size"};
                my $recv_sizes = join(" ", @{$action->{"recv_sizes"}});
                print("$task $type $send_size $recv_sizes\n");
            }

            case ["reducescatter"] {
                # FORMAT: <rank> reduceScatter <recv_sizes†> <comp_size> [<datatype>]
                my $recv_sizes = join(" ", @{$action->{"recv_sizes"}});
                my $comp_size = $action->{"comp_size"};
                print("$task $type $recv_sizes $comp_size\n");
            }

            default {
                die "<missing treatment of ", "$type>\n";
            }
        }
    }

}


sub define_v_fields
{
  
    # hash of communicators
    for my $comm (keys %v_actions) {
#        print "=> $comm\n";
        # hash of tasks
        for my $task (keys %{$v_actions{$comm}}){
#            print "  => $task\n";
            # hash of mpicalls
            for my $mpi_call (keys %{$v_actions{$comm}{$task}}){
#                print "    => $mpi_call\n";
                # array of requests (which are HASHes)
                my $index = 0;
                for my $elem (@{$v_actions{$comm}{$task}{$mpi_call}}){
#                    print "[$index]       => $elem\n";
#                    print Dumper($v_counts{$comm}{$mpi_call}[$index]);
                    $elem->{"recv_sizes"} = @{$v_counts{$comm}{$mpi_call}}[$index];
#                    print Dumper($elem);
                    $index++;
                }
            }
        }
    }
}

sub define_each_ptp_partner_comm_size
{
    my($task_send, $task_recv, $comm_size) = @_;

    # deal with send action
    my $send_action = \%{@{$ptp_partner_comm{$task_send}{"send"}}[0]};
    $send_action->{"partner"} = $task_recv;
    $send_action->{"comm_size"} = $comm_size;
    shift @{$ptp_partner_comm{$task_send}{"send"}};

    # deal with recv action
    my $recv_action = \%{@{$ptp_partner_comm{$task_recv}{"recv"}}[0]};
    $recv_action->{"partner"} = $task_send;
    $recv_action->{"comm_size"} = $comm_size;
    shift @{$ptp_partner_comm{$task_recv}{"recv"}};
    return;

}

sub define_ptp_partner_comm_size
{
    for my $elem (@ptp_operations_order){
        my $send = $elem->{"task_send"};
        my $recv = $elem->{"task_recv"};
        my $size = $elem->{"comm_size"};
        define_each_ptp_partner_comm_size ($send, $recv, $size);
    }
    return;

    
    print "====\n";
    print Dumper(@ptp_operations_order);
    print "===========\n";
    print Dumper(%ptp_partner_comm);
    print "====\n";
    return;

}

sub define_collective_root
{
    # hash of communicators
    for my $comm (keys %collective_root) {
        # hash of tasks
        for my $task (keys %{$collective_root{$comm}}){
            # hash of mpicalls
            for my $mpi_call (keys %{$collective_root{$comm}{$task}}){
                # array of requests (which are HASHes)
                my $index = 0;
                for my $elem (@{$collective_root{$comm}{$task}{$mpi_call}}){
                    $elem->{'root'} = $collective_root_order{$comm}{$mpi_call}[$index];
                    $index++;
                }
            }
        }
    }
    return;
}

sub main {
    my($arg);
    
    while(defined($arg = shift(@ARGV))) {
        for ($arg) {
            if (/^-i$/) { $input = shift(@ARGV); last; }
            print "unrecognized argument '$arg'\n";
        }
    }
    if(!defined($input) || $input eq "") { die "No valid input file provided.\n"; }
    
    parse_pcf($input.".pcf");
    parse_prv_lucas ($input.".prv");

    dump_tit_lucas();
    
    print STDERR "Translated events:\n";
    print STDERR join ", ", keys %translated_events;
    print STDERR "\nIgnored events:\n";
    print STDERR join ", ", keys %ignored_events;
    print STDERR "\n";
}

my %mpi_call_parameters = (
    "send size" => "50100001",
    "recv size" => "50100002",
    "root" => "50100003",
    "communicator" => "50100004",
    );

my @mpi_calls = (
    "MPI_Finalize",       #
    "MPI_Init",           #
    "MPI_Send",           #
    "MPI_Recv",           #
    "MPI_Isend",          #
    "MPI_Irecv",          #
    "MPI_Wait",           #
    "MPI_Waitall",        #
    "MPI_Bcast",          #
    "MPI_Reduce",         #
    "MPI_Allreduce",      #
    "MPI_Barrier",        #
    "MPI_Gather",         #
    "MPI_Allgather",      #
    "MPI_Alltoall",       #
    "MPI_Gatherv",        #
    "MPI_Allgatherv",     #
    "MPI_Reduce_scatter", #
    # "MPI_Alltoallv"
    );


# search for a MPI call in the event's parameters
# in all the cases I have seen, the event type and value are the first
# numbers in the event's parameter list, however we are not making this
# assumption. Instead, we look at all parameters and search for the one
# that is encoding the MPI call
sub extract_mpi_call {
    my %event_info = @_;
    
    # search for a MPI call in the event's parameters
    foreach my $key (keys %event_info) {
  if(defined($events{$key})) {
      if(defined($events{$key}{value}{$event_info{$key}})) {
    my $event_name = $events{$key}{value}{$event_info{$key}};
    if(grep(/^$event_name$/, @mpi_calls)) {
        $translated_events{$event_name} = 1;
        return $event_name;
    }
    else {
        $ignored_events{$event_name} = 1;
    }
      }
  }
    }
    return "None";
}

sub translate_from_mpi_to_tit_type
{
    my $mpi_call = @_;
    print "===> $mpi_call\n";
    $mpi_call =~ s/MPI_/LUCAS/g;
    print "==> $mpi_call\n";
    return $mpi_call;
}

sub generate_tit {
    my($task) = @_;
    $task = $task - 1;

    # keep translating until some MPI call is still missing some parameters
    while (1) {
  if (! (defined $task_states_buffer[$task])) { last; }
  if (scalar @{$task_states_buffer[$task]} == 0) { last; }
  my $state_entry = $task_states_buffer[$task][0];

  # if current state is running, generate tit entry, remove state and continue translating
  if ($state_entry->{"state"} eq "Running") {
      my $comp_size = ($state_entry->{"end_time"} - $state_entry->{"begin_time"}) * $power_reference;
      my $time = $state_entry->{"begin_time"};
            # PRINT compute
      print("$task compute $comp_size\n");
      shift(@{$task_states_buffer[$task]});
      next;
  }

  # if there are no events in the buffer and more than one state,
  # remove all states but the last one and continue
  if (scalar @{$task_events_buffer[$task]} == 0
      && scalar @{$task_states_buffer[$task]} > 1) {
      shift(@{$task_states_buffer[$task]});
      next;   
  }

  # if there are no events in the buffer, stop
  if (scalar @{$task_events_buffer[$task]} == 0) {
      last;
  }

  # remove current state if it does not contain any event and continue
  my $event_entry = $task_events_buffer[$task][0];
  if (!($state_entry->{"begin_time"} <= $event_entry->{"time"}
      && $state_entry->{"end_time"} > $event_entry->{"time"})) {
      shift(@{$task_states_buffer[$task]});
      next;
  }
  my $mpi_call = $event_entry->{"mpi_call"};
        
  # if event is a mpi v operation
  # check if other tasks already permormed that operation using the communicator v operation buffer
  if ($mpi_call eq "MPI_Gatherv" || $mpi_call eq "MPI_Allgatherv"
      || $mpi_call eq "MPI_Reduce_scatter" || $mpi_call eq "MPI_Alltoallv") {


      my @task_list = @{$communicators{$event_entry->{"communicator"}}{tasks}};
      my $action_ready = 1;
      for (my $i = 0; $i < scalar @task_list; $i++) {
    if (! (defined($communicators{$event_entry->{"communicator"}}{$mpi_call}{$task_list[$i]}))) {
        $action_ready = 0;
        last;
    }
    if (scalar @{$communicators{$event_entry->{"communicator"}}{$mpi_call}{$task_list[$i]}} == 0) {
        $action_ready = 0;
        last;
    } 
      }
      if ($action_ready == 0) {
    last;
      }

      my @recv_counts;
      my @send_counts;
      my $root;
      for (my $i = 0; $i < scalar @task_list; $i++) {
    push(@recv_counts, $communicators{$event_entry->{"communicator"}}{$mpi_call}{$task_list[$i]}[0]{"recv_size"});
    push(@send_counts, $communicators{$event_entry->{"communicator"}}{$mpi_call}{$task_list[$i]}[0]{"send_size"});
    if (! (defined($root))) {
        $root = $communicators{$event_entry->{"communicator"}}{$mpi_call}{$task_list[$i]}[0]{"root"};
    }

    my $use_count = $communicators{$event_entry->{"communicator"}}{$mpi_call}{$task_list[$i]}[0]{"use_count"} + 1;
    $communicators{$event_entry->{"communicator"}}{$mpi_call}{$task_list[$i]}[0]{"use_count"} = $use_count;
    if ($use_count == $communicators{$event_entry->{"communicator"}}{size}) {
        shift(@{$communicators{$event_entry->{"communicator"}}{$mpi_call}{$task_list[$i]}});
    }
      }

      switch ($mpi_call) {
    case "MPI_Gatherv" {
        # FORMAT: <rank> gatherV <send_size> <recv_sizes†> <root> [<send_datatype> <recv_datatype>]
        my $send_size = $event_entry->{"send_size"};
        my $recv_sizes = join(" ", @send_counts);
                    
        $root = $root - 1;
                    # PRINT gatherV
        print("$task gatherV $send_size $recv_sizes $root\n");
    }
    case "MPI_Allgatherv" {
        # FORMAT: <rank> allGatherV <send_size> <recv_sizes†> [<send_datatype> <recv_datatype>]
        my $send_size = $event_entry->{"send_size"};
        my $recv_sizes = join(" ", @send_counts);
                    # PRINT allGatherV
        print("$task allGatherV $send_size $recv_sizes\n");
    }
    case "MPI_Reduce_scatter" {
        # FORMAT: <rank> reduceScatter <recv_sizes†> <comp_size> [<datatype>]
        my $recv_sizes = join(" ", @recv_counts);
                    # PRINT reduceScatter
        print("$task reduceScatter $recv_sizes <comp_size>\n");
    }
      }

      shift(@{$task_events_buffer[$task]});
      shift(@{$task_states_buffer[$task]});
      next;
  }

  # if event is a mpi point to point communication
  # check if the p2p communication is on the communications buffer
  if ($mpi_call eq "MPI_Send" || $mpi_call eq "MPI_Recv"
      || $mpi_call eq "MPI_Isend" || $mpi_call eq "MPI_Irecv") {
      my $found_communication = 0;

      # if communication buffer is empty, stop translating
      if (! defined $task_comms_buffer[$task]) {
    last;
      }

      for (my $j = 0; $j < scalar @{$task_comms_buffer[$task]}; $j++) {
    my $comm_entry = $task_comms_buffer[$task][$j];
    if ($state_entry->{"begin_time"} <= $comm_entry->{"time"}
          && $state_entry->{"end_time"} >= $comm_entry->{"time"}) {
        $found_communication = 1;

        # if it is on the communication buffer
        # generate the tit entry and remove the state + event + comm entries
        my $time = $event_entry->{"time"};
        switch ($mpi_call) {
      case "MPI_Send" {
          # FORMAT: <rank> send <dst> <comm_size> [<datatype>]
          my $dst = $comm_entry->{"destiny"} - 1;
          my $comm_size = $comm_entry->{"comm_size"};
                            # PRINT send
          print("$task send $dst $comm_size\n");
      }
      case "MPI_Recv" {
          # FORMAT: <rank> recv <src> <comm_size> [<datatype>]
          my $src = $comm_entry->{"source"} - 1;
          my $comm_size = $comm_entry->{"comm_size"};
                            # PRINT recv
          print("$task recv $src $comm_size\n");
      }
      case "MPI_Isend" {
          # FORMAT: <rank> Isend <dst> <comm_size> [<datatype>]
          my $dst = $comm_entry->{"destiny"} - 1;
          my $comm_size = $comm_entry->{"comm_size"};
                            # PRINT Isend
          print("$task Isend $dst $comm_size\n");
      }
      case "MPI_Irecv" {
          # FORMAT: <rank> Irecv <src> <comm_size> [<datatype>]
          my $src = $comm_entry->{"source"} - 1;
          my $comm_size = $comm_entry->{"comm_size"};
                            # PRINT Irecv
          print("$task Irecv $src $comm_size\n");
      }
        }
        splice(@{$task_comms_buffer[$task]}, $j, 1);
        shift(@{$task_events_buffer[$task]});
        shift(@{$task_states_buffer[$task]});
        last;
    }
      }

      # if communication was not found, stop translating
      if ($found_communication == 0) {
    last;
      }
      else {
    next;
      }
  }

  # if mpi call is not a p2p communication
  # generate a tit entry, remove the state + event and continue 
  my $time = $event_entry->{"time"};
  switch ($mpi_call) {
      case "MPI_Init" {
    # FORMAT: <rank> init [<set_default_double>]
                # PRINT init
    print("$task init\n");
      }
      case "MPI_Finalize" {
    # FORMAT: <rank> finalize
                # PRINT finalize
    print("$task finalize\n");
      }
      case "MPI_Wait" {
    # FORMAT: <rank> wait
                # PRINT wait
    print("$task wait\n");
      }
      case "MPI_Waitall" {
    # FORMAT: <rank> waitAll
                # PRINT waitAll
    print("$task waitAll\n");
      }
      case "MPI_Bcast" {
    # FORMAT: <rank> bcast <comm_size> [<root> [<datatype>]]
    my $comm_size = $event_entry->{"send_size"} || $event_entry->{"recv_size"};
    my $root = $event_entry->{"root"};
                # PRINT bcast
    if (defined $root) {
        print("$task bcast $comm_size $task\n"); #BUG TODO
    }
    else {
        print("$task bcast $comm_size <ROOT>\n");
    }
      }
      case "MPI_Barrier" {
    # FORMAT: <rank> barrier
                # PRINT barrier
    print("$task barrier\n");
      }
      case "MPI_Reduce" {
    # FORMAT: <rank> reduce <comm_size> <comp_size> [<root> [<datatype>]]
    my $comm_size = $event_entry->{"send_size"} || $event_entry->{"recv_size"};
    my $root = $event_entry->{"root"};
                # PRINT reduce
    if (defined $root) {
        print("$task reduce $comm_size <comp_size> $task\n"); #BUG TODO
    }
    else {
        print("$task reduce $comm_size <comp_size>\n");
    }
      }
      case "MPI_Allreduce" {
    # FORMAT: <rank> allReduce <comm_size> <comp_size> [<datatype>]
    my $comm_size = $event_entry->{"send_size"} || $event_entry->{"recv_size"};
                # PRINT allReduce
    print("$task allReduce $comm_size <comp_size>\n");
      }
      case "MPI_Comm_split" {
    # FORMAT: <rank> comm_split
                # PRINT comm_split
    print("$task comm_split\n");
      }
      case "MPI_Comm_dup" {
    # FORMAT: <rank> comm_dup
                # PRINT comm_dup
    print("$task comm_dup\n");
      }
      case "MPI_Gather" {
    # FORMAT: <rank> gather <send_size> <recv_size> <root> [<send_datatype> <recv_datatype>]
    my $send_size = $event_entry->{"send_size"};
    my $recv_size = $event_entry->{"recv_size"};
    my $root = $event_entry->{"root"};
                # PRINT gather
    if (defined $root) {
        print("$task gather $send_size $recv_size $task\n"); #BUG TODO
    }
    else {
        print("$task gather $send_size $recv_size\n");
    }
      }
      case "MPI_Allgather" {
    # FORMAT: <rank> allGather <send_size> <recv_size> [<send_datatype> <recv_datatype>]
    my $send_size = $event_entry->{"send_size"};
    my $recv_size = $event_entry->{"recv_size"};
                # PRINT allGather
    print("$task allGather $send_size $recv_size\n");
      }
      case "MPI_Alltoall" {
    # FORMAT: <rank> allToAll <send_size> <recv_recv> [<send_datatype> <recv_datatype>]
    my $send_size = $event_entry->{"send_size"};
    my $recv_size = $event_entry->{"send_size"};
                # PRINT alltoall
    print("$task alltoall $send_size $recv_size\n");
      }
  }
  shift(@{$task_events_buffer[$task]});
  shift(@{$task_states_buffer[$task]});
    }
}

# This function add a state to the corresponding task state buffer
# It is called for every paraver line starting with ^1
sub add_state_entry {
    my($task, %parameters) = @_;

    my $begin_time = $parameters{"begin_time"};
    my $end_time = $parameters{"end_time"};
    my $state = $parameters{"state"};

    # create an entry (hash table) to be added to the state buffer of this task
    # at the end, this buffer will looks like a gantt chart with states only
    my %entry;
    $entry{"begin_time"} = $begin_time;
    $entry{"end_time"} = $end_time;
    $entry{"state"} = $state;

    push @{ $task_states_buffer[$task - 1] }, \%entry;
}

# This function is called for lines starting with 2.
sub add_event_entry {
    my($task, %parameters) = @_;

    my $time = $parameters{"time"};
    my $mpi_call = $parameters{"mpi_call"};
    my $send_size = $parameters{"send_size"};
    my $recv_size = $parameters{"recv_size"};
    my $root = $parameters{"root"};
    my $communicator = $parameters{"communicator"};

    my %entry;
    $entry{"time"} = $time;
    $entry{"mpi_call"} = $mpi_call;
    $entry{"send_size"} = $send_size;
    $entry{"recv_size"} = $recv_size;
    $entry{"root"} = $root;
    $entry{"communicator"} = $communicator;
    push @{ $task_events_buffer[$task - 1] }, \%entry;

    
    # if event is a MPI_Bcast operation
    # Create buffer entry for it in the communicator entry
    if ($mpi_call eq "MPI_Bcast"){     
        my %bcast_operation_entry;
        $bcast_operation_entry{"time"} = $time;
        $bcast_operation_entry{"comm_size"} = $send_size > $recv_size ? $send_size : $recv_size;
        if (defined $root){
            $bcast_operation_entry{"root"} = $root;
        }
        push @{ $communicators{$communicator}{$mpi_call}{$task} }, \%bcast_operation_entry;
        # print ("task", Dumper($communicators{$communicator}{$mpi_call}{$task}));

        # for every $communicator $mpi_call $task array which has root undefined, define root
#         if (defined $root){
#             print "Looping over $communicator $mpi_call\n";

#             while(my($key, @array) = each $communicators{$communicator}{$mpi_call}) {
#                 foreach (@array){
#                     print $_{time};
#                 }

                
# #                 print ("Loop $key =", Dumper($array), "\n");
# #                 foreach my $bcast_entry ($array) {                    
# #                     print ("here we go ", Dumper($bcast_entry));
# # #                    if (!defined $bcast_entry{"root"}){
# #                         #                        $bcast_entry{"root"} = $root;
# #  #                   }
#             }
#         }else{
#             # search for root if it is already defined, if it is, use it to define

#             # foreach my $hash ($communicators{$communicator}{$mpi_call}){
#             #     print "Loop\n";
#             #     print Dumper($hash);
#             #     print Dumper(ref($hash));
#             # }
#         }
        
#         if (!defined $root){


            
#             # task $task has a MPI_Bcast with an undefined root, have to wait for it to appear
#             # it will only appear when the actual event from the broadcast root appears
#             # so buffer to wait



            
#             my $size;
#             $size = $bcast_operation_entry{"comm_size"};
#             print "task $task has a MPI_Bcast with an undefined root (message size $size), have to wait for it to appear\n";
#         }else{
#             # task $task appeared with a defined root of $root
#             # have to look for in the communicators buffer

#             print "task $task appeared with a defined root of $root\n";

#             my $s;
#             $s = keys $communicators{$communicator}{$mpi_call};
#             print ("task: Size of $communicator $mpi_call hash is $s\n");
            
# #            print Dumper($communicators{$communicator}{$mpi_call});

#  #           foreach my $t (1..$number_of_tasks) {
#   #              print "$t\n";
# #
#  #           }


            
#   #          print "$number_of_tasks\n";
            
#         }

    }
    
    
    # if event is a mpi v operations
    # create buffer entry for it in the communicator entry
    if ($mpi_call eq "MPI_Gatherv" || $mpi_call eq "MPI_Allgatherv"
  || $mpi_call eq "MPI_Reduce_scatter") {
  my %v_operation_entry;
  $v_operation_entry{"time"} = $time;
  $v_operation_entry{"send_size"} = $send_size;
  $v_operation_entry{"recv_size"} = $recv_size;
  if (defined $root) {
    $v_operation_entry{"root"} = $task;
  }
  else {
    $v_operation_entry{"root"} = undef;
  }
  $v_operation_entry{"use_count"} = 0;
  push @{ $communicators{$communicator}{$mpi_call}{$task} }, \%v_operation_entry;
    }
}

sub add_communication_entry {
    my($task_send, $task_recv, %parameters) = @_;

    my $time_send = $parameters{"time_send"};
    my $time_recv = $parameters{"time_recv"};
    my $comm_size = $parameters{"comm_size"};
    my $source = $parameters{"source"};
    my $destiny = $parameters{"destiny"};

    my %entry_send;
    $entry_send{"time"} = $time_send;
    $entry_send{"comm_size"} = $comm_size;
    $entry_send{"destiny"} = $destiny;
    push @{ $task_comms_buffer[$task_send - 1] }, \%entry_send;

    my %entry_recv;
    $entry_recv{"time"} = $time_recv;
    $entry_recv{"comm_size"} = $comm_size;
    $entry_recv{"source"} = $source;
    push @{ $task_comms_buffer[$task_recv - 1] }, \%entry_recv;
}


sub parse_prv {
    my($prv) = @_; # get arguments
    open(INPUT, $prv) or die "Cannot open $prv. $!";

    # check if header is valid, we should get something like #Paraver (dd/mm/yy at hh:m):ftime:0:nAppl:applicationList[:applicationList]
    my $line = <INPUT>;
    chomp $line;
    $line =~ /^\#Paraver / or die "Invalid header '$line'\n";
    my $header = $line;
    $header =~ s/^[^:\(]*\([^\)]*\):// or die "Invalid header '$line'\n";
    $header =~ s/(\d+):(\d+)([^\(\d])/$1\_$2$3/g;
    $header =~ s/,\d+$//g;
    my($max_duration, $resource, $number_of_apps, @app_info_list) = split(/:/, $header);
    $max_duration =~ s/_.*$//g;
    $resource =~ /^(.*)\((.*)\)$/ or die "Invalid resource description '$resource'\n";
    my($number_of_nodes, $node_cpu_count) = ($1, $2);
    $number_of_apps == 1 or die "Only one application can be handled at the moment\n";
    my @node_cpu_count = split(/,/, $node_cpu_count);

    # parse app info
    foreach my $app (1..$number_of_apps) {
        $app_info_list[$app - 1] =~ /^(.*)\((.*)\)$/ or die "Invalid application description\n";
  my $task_info;
        ($number_of_tasks, $task_info) = ($1, $2);
        my(@task_info_list) = split(/,/, $task_info);

        # initiate an empty event buffer for each task
  @task_events_buffer = (0);
        foreach my $task (1..$number_of_tasks) {
            my($number_of_threads, $node) = split(/_/, $task_info_list[$task - 1]);
      my @buffer;
      $task_events_buffer[$task - 1] = \@buffer;
        } 
    }

    # start reading records
    while(defined($line=<INPUT>)) {
        chomp $line;

        # state records are in the format 1:cpu:appl:task:thread:begin_time:end_time:state_id
        # they keep states along time for each cpu/appl/task/thread
        if($line =~ /^1/) {
            my($record, $cpu, $appli, $task, $thread, $begin_time, $end_time, $state_id) = split(/:/, $line);
      my $state_name = $states{$state_id}{name};

      generate_tit($task);

      my %parameters;
      $parameters{"begin_time"} = $begin_time;
      $parameters{"end_time"} = $end_time;
      $parameters{"state"} = $state_name;
      add_state_entry($task, %parameters);
        }

  # event records are in the format 2:cpu:appl:task:thread:time:event_type:event_value
        # => multiple event_type:event_value might be present
        # these keep a number of events (MPI or others)
  elsif ($line =~ /^2/) {
      my($record, $cpu, $appli, $task, $thread, $time, %event_list) = split(/:/, $line);
      my $mpi_call = extract_mpi_call(%event_list);

      # if event is a MPI call, get the MPI call parameters and add_event_entry($task, %parameters);
      if($mpi_call ne "None") {
                my $event_list;                
    my $send_size = $event_list{$mpi_call_parameters{"send size"}};
    my $recv_size = $event_list{$mpi_call_parameters{"recv size"}};
                # TODO SUD6: Next line is not working (root appears only for the root of the collective operation)
                # We should buffer this according to a combination of task/communicator waiting for the root data appears
    my $root = $event_list{$mpi_call_parameters{"root"}};
    my $comm = $event_list{$mpi_call_parameters{"communicator"}};
                
    my %parameters;
    $parameters{"time"} = $time;
    $parameters{"mpi_call"} = $mpi_call;
    $parameters{"send_size"} = $send_size;
    $parameters{"recv_size"} = $recv_size;
    $parameters{"root"} = $root;
    $parameters{"communicator"} = $comm;
    add_event_entry($task, %parameters);
      }
        }

  # communication records are in the format 3:cpu_send:ptask_send:task_send:thread_send:logical_time_send:actual_time_send:cpu_recv:ptask_recv:task_recv:thread_recv:logical_time_recv:actual_time_recv:size:tag
  elsif($line =~ /^3/) { 
           my($record, $cpu_send, $ptask_send, $task_send, $thread_send, $ltime_send, $atime_send, $cpu_recv, $ptask_recv, $task_recv, $thread_recv, $ltime_recv, $atime_recv, $size, $tag) = split(/:/, $line);
     # get mpi call parameters from the communication entry
     my %parameters;
     $parameters{"time_send"} = $ltime_send;
     $parameters{"time_recv"} = $ltime_recv;
     $parameters{"comm_size"} = $size;
     $parameters{"source"} = $task_send;
     $parameters{"destiny"} = $task_recv;

           add_communication_entry($task_send, $task_recv, %parameters);
        }

  # communicator record are in the format c:app_id:communicator_id:number_of_process:thread_list (e.g., 1:2:3:4:5:6:7:8)
        if($line =~ /^c/) {
            my($record, $appli, $id, $size, @task_list) = split(/:/, $line);
      $communicators{$id} = { 'size' => $size };
      $communicators{$id}{tasks} = [@task_list];
        }
    }

    for my $task (1 .. $number_of_tasks) {
  generate_tit($task);
    }

    return;
}

sub register_v_count
{
    my ($comm, $mpi_call, $task, $send_size) = @_;
#    print "Operation $mpi_call found, have to add $send_size to position $task of recv sizes on $comm/$mpi_call\n";

    # -1 because paraver does not start at zero
    $task--;
    
    # array (indicating order of operations) of arrays (with the message sizes)
    if (!defined $v_counts{$comm}{$mpi_call}){
        # only the first time, when the array of operations does not exist
        my @ar;
        @ar[$task] = $send_size;
        push @{$v_counts{$comm}{$mpi_call}}, \@ar;
    }else{
        # ok, operation order array already exists, search for array to put value $send_size at $task position
        # in other words, I have to look for the first array where $task position is undef

        my $found = 0;
        my $index = 0;
        for my $elem (@{$v_counts{$comm}{$mpi_call}}){
            if (!defined @{$elem}[$task]){
#                print "Position $task is not defined.\n";
                @{$elem}[$task] = $send_size;
                $found = 1;
                last;
            }
            $index++;
        }
        if (!$found){
#            print ("Go to the end of the array of operations and were unabled to find a position, create a new one.\n");
            my @ar;
            @ar[$task] = $send_size;
            push @{$v_counts{$comm}{$mpi_call}}, \@ar;
        }
    }
}


sub register_root {
    my ($comm, $task, $mpi_call, $root, $action) = @_;
                        
    # generic way of dealing with root (for those tit events that needs it)
    if (defined $root){
        $action->{"root"} = $task;
        push @{$collective_root_order{$comm}{$mpi_call}}, $task;
    }
    push @{$collective_root{$comm}{$task}{$mpi_call}}, $action;
}

sub parse_prv_lucas {
    my($prv) = @_; # get arguments
    open(INPUT, $prv) or die "Cannot open $prv. $!";

    # check if header is valid, we should get something like #Paraver (dd/mm/yy at hh:m):ftime:0:nAppl:applicationList[:applicationList]
    my $line = <INPUT>;
    chomp $line;
    $line =~ /^\#Paraver / or die "Invalid header '$line'\n";
    my $header = $line;
    $header =~ s/^[^:\(]*\([^\)]*\):// or die "Invalid header '$line'\n";
    $header =~ s/(\d+):(\d+)([^\(\d])/$1\_$2$3/g;
    $header =~ s/,\d+$//g;
    my($max_duration, $resource, $number_of_apps, @app_info_list) = split(/:/, $header);
    $max_duration =~ s/_.*$//g;
    $resource =~ /^(.*)\((.*)\)$/ or die "Invalid resource description '$resource'\n";
    my($number_of_nodes, $node_cpu_count) = ($1, $2);
    $number_of_apps == 1 or die "Only one application can be handled at the moment\n";
    my @node_cpu_count = split(/,/, $node_cpu_count);

    # parse app info
    foreach my $app (1..$number_of_apps) {
        $app_info_list[$app - 1] =~ /^(.*)\((.*)\)$/ or die "Invalid application description\n";
  my $task_info;
        ($number_of_tasks, $task_info) = ($1, $2);
        my(@task_info_list) = split(/,/, $task_info);

        # initiate an empty event buffer for each task
  @task_events_buffer = (0);
        foreach my $task (1..$number_of_tasks) {
            my($number_of_threads, $node) = split(/_/, $task_info_list[$task - 1]);
      my @buffer;
      $task_events_buffer[$task - 1] = \@buffer;
        } 
    }

    # LUCAS version LUCAS
    # start reading records
    while(defined($line=<INPUT>)) {
        chomp $line;

        # state records are in the format 1:cpu:appl:task:thread:begin_time:end_time:state_id
        # they keep states along time for each cpu/appl/task/thread
        if($line =~ /^1/) {
            my($record, $cpu, $appli, $task, $thread, $begin_time, $end_time, $state_id) = split(/:/, $line);
      my $state_name = $states{$state_id}{name};

            if ($state_name eq "Running"){
                my $comp_size = ($end_time - $begin_time) * $power_reference;

                my %action_compute;
                $action_compute{"type"} = "compute";
                $action_compute{"comp_size"} = $comp_size;
                $action_compute{"task"} = $task;
                push @action_buffer, \%action_compute;
            }
        }
        
  # event records are in the format 2:cpu:appl:task:thread:time:event_type:event_value
        # => multiple event_type:event_value might be present
        # these keep a number of events (MPI or others)
        # LUCAS
        elsif($line =~ /^2/){
      my($record, $cpu, $appli, $task, $thread, $time, %event_list) = split(/:/, $line);
      my $mpi_call = extract_mpi_call(%event_list);

      # if event is a MPI call, get the MPI call parameters and add_event_entry($task, %parameters);
      if($mpi_call ne "None") {

                # the action to be pushed (a HASH)
                my %action;

                # start preparation of the task
                # define the task and its type
                $action{"task"} = $task;
                my $teste;
                $teste = $mpi_call;
                $teste =~ s/MPI_//;
                $teste = lc($teste);
                $action{"type"} = $teste;

                # extract information from this paraver event
                my $event_list;                
    my $send_size = $event_list{$mpi_call_parameters{"send size"}};
    my $recv_size = $event_list{$mpi_call_parameters{"recv size"}};
    my $root = $event_list{$mpi_call_parameters{"root"}}; #marker present in the root
    my $comm = $event_list{$mpi_call_parameters{"communicator"}};

                # register root
                switch ($mpi_call) {
                    case ["MPI_Bcast", "MPI_Gather", "MPI_Reduce", "MPI_Gatherv"] {
                        $action{"root"} = undef;

                        # register the root for backpatching
                        register_root ($comm, $task, $mpi_call, $root, \%action);
                    }
                }

                # register ptp info
                switch ($mpi_call){
                    case ["MPI_Send", "MPI_Isend"] {
                        push @{$ptp_partner_comm{$task}{"send"}}, \%action;
                    }

                    case ["MPI_Recv", "MPI_Irecv"] {
                        push @{$ptp_partner_comm{$task}{"recv"}}, \%action;
                    }
                }

                # remaining parameters
                switch ($mpi_call) {
                    case ["MPI_Init", "MPI_Finalize"] {
                        # nothing particular to do
                    }

                    case ["MPI_Bcast"] {
                        $action{"comm_size"} = $send_size > $recv_size ? $send_size : $recv_size;
                    }

                    case ["MPI_Send", "MPI_Recv", "MPI_Isend", "MPI_Irecv"] {
                        $action{"partner"} = undef;
                        $action{"comm_size"} = undef;
                    }

                    case ["MPI_Allreduce", "MPI_Reduce"] {
                        $action{"comm_size"} = $send_size > $recv_size ? $send_size : $recv_size; # TODO
                        $action{"comp_size"} = 0;     # where should we take this information from?
                    }

                    case ["MPI_Gather", "MPI_Allgather", "MPI_Alltoall"] {
                        $action{"send_size"} = $send_size;
                        $action{"recv_size"} = $recv_size;
                    }

                    case ["MPI_Allgatherv", "MPI_Gatherv"] {
                        $action{"send_size"} = $send_size;
                        $action{"recv_sizes"} = undef;

                        # the action that should be backpatched
                        push @{$v_actions{$comm}{$task}{$mpi_call}}, \%action;

                        # the information that should be used to backpatch
                        register_v_count ($comm, $mpi_call, $task, $send_size);
                    }

                    case ["MPI_Reduce_scatter"] {
                        $action{"comp_size"} = 0;     # where should we take this information from?

                        # the action that should be backpatched
                        push @{$v_actions{$comm}{$task}{$mpi_call}}, \%action;

                        # the information that should be used to backpatch
                        register_v_count ($comm, $mpi_call, $task, $recv_size);
                    }
                }
                
                # push to the action array (everything is buffered before dump at the end)
                push @action_buffer, \%action;
      }
        }
        # communication records are in the format 3:cpu_send:ptask_send:task_send:thread_send:logical_time_send:actual_time_send:cpu_recv:ptask_recv:task_recv:thread_recv:logical_time_recv:actual_time_recv:size:tag
  elsif($line =~ /^3/) { 
           my($record, $cpu_send, $ptask_send, $task_send, $thread_send, $ltime_send, $atime_send, $cpu_recv, $ptask_recv, $task_recv, $thread_recv, $ltime_recv, $atime_recv, $size, $tag) = split(/:/, $line);
     # get mpi call parameters from the communication entry

           my %ptp_operation;
           $ptp_operation{"task_send"} = $task_send;
           $ptp_operation{"task_recv"} = $task_recv;
           $ptp_operation{"comm_size"} = $size;
           push @ptp_operations_order, \%ptp_operation;
        }

        next;
        
  # communicator record are in the format c:app_id:communicator_id:number_of_process:thread_list (e.g., 1:2:3:4:5:6:7:8)
        if($line =~ /^c/) {
            my($record, $appli, $id, $size, @task_list) = split(/:/, $line);
      $communicators{$id} = { 'size' => $size };
      $communicators{$id}{tasks} = [@task_list];
        }
    }

    # for my $task (1 .. $number_of_tasks) {
    #     generate_tit($task);
    # }

    return;
}



sub parse_pcf {
    my($pcf) = shift; # get first argument
    my $line;

    open(INPUT, $pcf) or die "Cannot open $pcf. $!";
    while(defined($line=<INPUT>)) {
        chomp $line; # remove new line
        if($line =~ /^STATES$/) {
            while((defined($line=<INPUT>)) && ($line =~ /^(\d+)\s+(.*)/g)) {
                $states{$1}{name} = $2;
    $states{$1}{used} = 0;
            }
        }

        if($line =~ /^EVENT_TYPE$/) {
      my $id;
            while($line=<INPUT>) { # read event
                if($line =~ /VALUES/g) {
        while((defined($line=<INPUT>)) && ($line =~ /^(\d+)\s+(.*)/g)) { # read event values
      $events{$id}{value}{$1} = $2;
        }
        last;
    }
                $line =~ /[\d]\s+(\d+)\s+(.*)/g or next;
                $id = $1;
                $events{$id}{type} = $2;
    $events{$id}{used} = 0;
            }
        }
    }

    #print Dumper(\%states);
    #print Dumper(\%events);
}


main();

