#include <stdio.h>
#include <mpi.h>
#include <string>

using namespace std;

int main(int argc, char * argv[])
{
    MPI_Init(&argc, &argv);

    int rank;
    int size;

    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    printf("rank=%d, size=%d\n", rank, size);

    // Sending size-1 integers from each rank != 0 to 0 (gather)
    if (rank == 0)
    {
        for (int i = 1; i < size; ++i)
        {
            int u;
            MPI_Recv(&u, 1, MPI_INT, i, 0, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        }
    }
    else
    {
        MPI_Send(&rank, 1, MPI_INT, 0, 0, MPI_COMM_WORLD);
    }

    MPI_Barrier(MPI_COMM_WORLD);

    // Now doing a real gather !
    int nb_elements = 5;
    int buf_gather[nb_elements * size];

    for (int i = 0; i < nb_elements; ++i)
        buf_gather[i] = rank;

    MPI_Gather(buf_gather, nb_elements, MPI_INT, buf_gather, nb_elements, MPI_INT, 0, MPI_COMM_WORLD);

    if (rank == 0)
    {
        string s = "Gather:";
        for (int i = 0; i < nb_elements * size; ++i)
            s += " " + to_string(buf_gather[i]);
        printf("%s\n", s.c_str());
    }

    MPI_Barrier(MPI_COMM_WORLD);

    // Broadcast time!
    nb_elements = 3;
    int buf_bcast[nb_elements];

    if (rank == 0)
    {
        for (int i = 0; i < nb_elements; ++i)
            buf_bcast[i] = i * 10;
    }

    MPI_Bcast(buf_bcast, nb_elements, MPI_INT, 0, MPI_COMM_WORLD);

    if (true)
    {
        string s = "Bcast, rank=" + to_string(rank) + ':';

        for (int i = 0; i < nb_elements; ++i)
            s += " " + to_string(buf_bcast[i]);
        printf("%s\n", s.c_str());
    }

    MPI_Barrier(MPI_COMM_WORLD);

    // Scatter time
    nb_elements = 2;
    int buf_scatter[nb_elements*size];

    if (rank == 0)
        for (int i = 0; i < nb_elements * size; ++i)
            buf_scatter[i] = i;

    MPI_Scatter(buf_scatter, nb_elements, MPI_INT, buf_scatter, nb_elements, MPI_INT, 0, MPI_COMM_WORLD);

    // Reduce time
    int value = rank;
    int reduced_value;
    MPI_Reduce(&value, &reduced_value, 1, MPI_INT, MPI_SUM, 0, MPI_COMM_WORLD);

    if (rank == 0)
        printf("Reduce, rank=%d, value=%d\n", rank, reduced_value);

    MPI_Barrier(MPI_COMM_WORLD);

    // Allreduce time
    value = rank;
    reduced_value = -1;
    MPI_Allreduce(&value, &reduced_value, 1, MPI_INT, MPI_MAX, MPI_COMM_WORLD);
    printf("Allreduce, rank=%d, value=%d\n", rank, reduced_value);

    MPI_Barrier(MPI_COMM_WORLD);

    // Alltoall time!
    nb_elements = 2;
    int all_to_all_buf[nb_elements*size];
    int all_to_all_buf_recv[nb_elements * size] = {0};

    for (int i = 0; i < nb_elements*size; ++i)
        all_to_all_buf[i] = (rank+1) * 100 + i;

    string s = "Alltoall, rank=" + to_string(rank) + ",send_buf=";
    for (int i = 0; i < nb_elements*size; ++i)
        s += " " + to_string(all_to_all_buf[i]);
    printf("%s\n", s.c_str());

    MPI_Barrier(MPI_COMM_WORLD);

    MPI_Alltoall(all_to_all_buf, nb_elements, MPI_INT, all_to_all_buf_recv, nb_elements, MPI_INT, MPI_COMM_WORLD);

    s = "Alltoall, rank=" +to_string(rank) + ",recv_buf=";
    for (int i = 0; i < nb_elements * size; ++i)
        s += " " + to_string(all_to_all_buf_recv[i]);
    printf("%s\n", s.c_str());

    MPI_Finalize();

    return 0;
}
