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
from execo_engine import Engine, logger

script_path = os.path.dirname(os.path.realpath(__file__))

use_test_resources = True


def prediction_callback(ts):
    logger.info("job start prediction = %s" % (format_date(ts),))


class oar_replay_workload(Engine):

    def setup_result_dir(self):
        self.result_dir = script_path + '/results_' + \
                time.strftime("%Y-%m-%d--%H-%M-%S")

    def run(self):
        """Run the experiment"""
        if use_test_resources:
            logger.warn('THIS IS A TEST! This run will use only a few '
                        'resources')
        logger.info('reserving a cluster of nodes')

        cluster = 'graphene'
        switch = 'sgraphene4'
        env_name = "debian8_workload_generation_nfs"

        site = get_cluster_site(cluster)
        if use_test_resources:
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
                install_oar_nodes = Remote(install_cmd + node_packages, nodes,
                                           connection_params={'user': 'root'})
                install_oar_nodes.start()

                server_packages = "oar-server oar-server-pgsql oar-user oar-user-pgsql"
                logger.info("installing OAR server node: {}".format(str(nodes[0])))
                install_master = SshProcess(install_cmd + server_packages, nodes[0],
                                            connection_params={'user': 'root'})
                install_master.run()

                config_oar_cmd = """
                sed -i \
                    -e 's/^\(DB_TYPE\)=.*/\1="Pg"/' \
                    -e 's/^\(DB_HOSTNAME\)=.*/\1="server"/' \
                    -e 's/^\(DB_PORT\)=.*/\1="5432"/' \
                    -e 's/^\(DB_BASE_PASSWD\)=.*/\1="oar"/' \
                    -e 's/^\(DB_BASE_LOGIN\)=.*/\1="oar"/' \
                    -e 's/^\(DB_BASE_PASSWD_RO\)=.*/\1="oar_ro"/' \
                    -e 's/^\(DB_BASE_LOGIN_RO\)=.*/\1="oar_ro"/' \
                    -e 's/^\(SERVER_HOSTNAME\)=.*/\1="localhost"/' \
                    -e 's/^\(SERVER_PORT\)=.*/\1="16666"/' \
                    -e 's/^\(LOG_LEVEL\)\=\"2\"/\1\=\"3\"/' \
                    -e 's/^#\(JOB_RESOURCE_MANAGER_PROPERTY_DB_FIELD\=\"cpuset\".*\)/\1/' \
                    -e 's/^#\(CPUSET_PATH\=\"\/oar\".*\)/\1/' \
                    /etc/oar/oar.conf; \
                    oar-database --create --db-is-local
                """
                configure_oar = Remote(configure_oar_cmd, nodes,
                                         connection_params={'user': 'root'})
                configure_nodes.run()
                logger.info("OAR is configured on all nodes")

                # Add nodes to OAR cluster
                hostfile_filename = self.result_dir + '/' + 'hostfile'
                with open(hostfile_filename, 'w') as hostfile:
                    for node in nodes[1:]:
                        print>>hostfile, node.address
                add_resources_cmd = "oar_resources_init -y -x " + hostfile_filename
                add_resources = SshProcess(add_resources_cmd, nodes[0],
                                           connection_params={'user': 'root'})
                add_resources.run()

                logger.info("oar is now configured!")
                raise RuntimeError()

            except:
                traceback.print_exc()
                ipdb.set_trace()

            finally:
                logger.info("delete job: {}".format(jobs))
                oardel(jobs)

if __name__ == "__main__":
    engine = oar_replay_workload()
    engine.start()
