#!/usr/bin/env python2
"""
This script is running a complete OAR cluster deployment on Grid'5000 to
experiment OAR scheduling policies in real conditions using a replay tool
named *Riplay*.

It use the development version of an OAR scheduler name Kamelot

It give as an results information about scheduling that was done.
"""

import os
import time
import ipdb
import traceback
from execo import SshProcess, Remote, format_date
from execo_g5k import oarsub, oardel, OarSubmission, \
    get_oar_job_nodes, wait_oar_job_start, \
    get_cluster_site
from execo_g5k.kadeploy import deploy, Deployment
from execo_engine import Engine, logger, ParamSweeper, sweep

script_path = os.path.dirname(os.path.realpath(__file__))

is_a_test = True


def prediction_callback(ts):
    logger.info("job start prediction = %s" % (format_date(ts),))


class oar_replay_workload(Engine):

    def setup_result_dir(self):
        run_type = ""
        if is_a_test:
            run_type = "test"
        self.result_dir = script_path + '/' + run_type + 'results_' + \
                time.strftime("%Y-%m-%d--%H-%M-%S")

    def run(self):
        """Run the experiment"""
        if is_a_test:
            logger.warn('THIS IS A TEST! This run will use only a few '
                        'resources')

        cluster = 'graphene'
        switch = 'sgraphene4'
        env_name = "debian8_workload_generation_nfs"

        # define the parameters
        if is_a_test:
            workloads = ['test_profile.json']
        else:
            workloads = ['g5k_workload_delay' + num + '.json'
                         for num in range(0, 6)]

        self.parameters = {
            'workload_filenames': workloads
        }

        # define the iterator over the parameters combinations
        self.sweeper = ParamSweeper(os.path.join(self.result_dir, "sweeps"),
                                    sweep(self.parameters))

        # Due to previous (using -c result_dir) run skip some combination
        logger.info('Skipped parameters:' +
                    '{}'.format(str(self.sweeper.get_skipped())))

        logger.info('Number of parameters combinations {}'.format(
            str(len(self.sweeper.get_remaining()))))

        site = get_cluster_site(cluster)
        if is_a_test:
            jobs = oarsub([(OarSubmission(resources="/nodes=3",
                                          job_type='deploy',
                                          walltime='00:30:00'), site)])
        else:
            jobs = oarsub([(OarSubmission(resources="{switch='" + switch + "'}/switch=1",
                                          job_type='deploy',
                                          walltime='04:00:00'), site)])
        job_id, site = jobs[0]
        if job_id:
            try:
                logger.info("waiting job start %s on %s" % (job_id, site))
                wait_oar_job_start(job_id, site, prediction_callback=prediction_callback)
                logger.info("getting nodes of %s on %s" % (job_id, site))
                nodes = get_oar_job_nodes(job_id, site)
                logger.info("deploying nodes: {}".format(str(nodes)))
                deployed, undeployed = deploy(
                    Deployment(nodes, env_name=env_name))
                if undeployed:
                    logger.warn("NOT deployed nodes: {}".format(str(undeployed)))
                    raise RuntimeError('Deployement failed')

                # install OAR
                install_cmd = "apt-get install -y "
                node_packages = "oar-node"
                logger.info("installing OAR nodes: {}".format(str(nodes[1:])))
                install_oar_nodes = Remote(install_cmd + node_packages, nodes[1:],
                                           connection_params={'user': 'root'})
                install_oar_nodes.start()

                server_packages = "oar-server oar-server-pgsql oar-user oar-user-pgsql"
                logger.info("installing OAR server node: {}".format(str(nodes[0])))
                install_master = SshProcess(install_cmd + server_packages, nodes[0],
                                            connection_params={'user': 'root'})
                install_master.run()
                install_oar_nodes.wait()

                configure_oar_cmd = """
                sed -i \
                    -e 's/^\(DB_TYPE\)=.*/\\1="Pg"/' \
                    -e 's/^\(DB_HOSTNAME\)=.*/\\1="localhost"/' \
                    -e 's/^\(DB_PORT\)=.*/\\1="5432"/' \
                    -e 's/^\(DB_BASE_PASSWD\)=.*/\\1="oar"/' \
                    -e 's/^\(DB_BASE_LOGIN\)=.*/\\1="oar"/' \
                    -e 's/^\(DB_BASE_PASSWD_RO\)=.*/\\1="oar_ro"/' \
                    -e 's/^\(DB_BASE_LOGIN_RO\)=.*/\\1="oar_ro"/' \
                    -e 's/^\(SERVER_HOSTNAME\)=.*/\\1="localhost"/' \
                    -e 's/^\(SERVER_PORT\)=.*/\\1="16666"/' \
                    -e 's/^\(LOG_LEVEL\)\=\"2\"/\\1\=\"3\"/' \
                    -e 's/^#\(JOB_RESOURCE_MANAGER_PROPERTY_DB_FIELD\=\"cpuset\".*\)/\\1/' \
                    -e 's/^#\(CPUSET_PATH\=\"\/oar\".*\)/\\1/' \
                    /etc/oar/oar.conf
                """
                configure_oar = Remote(configure_oar_cmd, nodes,
                                       connection_params={'user': 'root'})
                configure_oar.run()
                logger.info("OAR is configured on all nodes")

                # Configure server
                create_db = "oar-database --create --db-is-local"
                start_oar = "systemctl start oar-server.service"
                logger.info("configuring OAR database: {}".format(str(nodes[0])))
                config_master = SshProcess(create_db + ";" + start_oar, nodes[0],
                                            connection_params={'user': 'root'})
                config_master.run()

                # Add nodes to OAR cluster
                hostfile_filename = self.result_dir + '/' + 'hostfile'
                with open(hostfile_filename, 'w') as hostfile:
                    for node in nodes[1:]:
                        print>>hostfile, node.address

                # Use this for new version of oar_resources_init
                # add_resources_cmd = "oar_resources_init -y -x " + hostfile_filename

                add_resources_cmd = "oar_resources_init -o /tmp/add_nodes " + \
                                    hostfile_filename + "<<EOF\ny\nEOF;. /tmp/add/nodes"
                add_resources = SshProcess(add_resources_cmd, nodes[0],
                                           connection_params={'user': 'root'})
                add_resources.run()

                if add_resources.ok():
                    logger.info("oar is now configured!")
                else:
                    raise RuntimeError("error in the OAR configuration: Abort!")

                # Do the replay
                while len(self.sweeper.get_remaining()) > 0:
                    combi = self.sweeper.get_next()
                    oar_replay = SshProcess("oar_replay" + combi['workload_filename'])
                    oar_replay.run()
                    if oar_replay.ok:
                        logger.info("Replay workload OK: {}".format(combi))
                        self.sweeper.done(combi)
                    else:
                        logger.info("Replay workload NOT OK: {}".format(combi))
                        self.sweeper.cancel(combi)

            except:
                traceback.print_exc()
                ipdb.set_trace()

            finally:
                logger.info("delete job: {}".format(jobs))
                oardel(jobs)

if __name__ == "__main__":
    engine = oar_replay_workload()
    engine.start()
