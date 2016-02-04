#!/usr/bin/env python
import os
from itertools import takewhile, count
from execo import SshProcess, Remote, Put, format_date
from execo_g5k import oarsub, oardel, OarSubmission, \
    get_oar_job_nodes, wait_oar_job_start, \
    get_host_attributes, get_cluster_site, get_host_site
from execo_g5k.kadeploy import deploy
from execo_engine import Engine, ParamSweeper, sweep, \
    slugify, logger

def prediction_callback(ts):
    logger.info("job start prediction = %s" % (format_date(ts),))

def get_mpi_opts(cluster):
    # MPI configuration depends on the cluster
    # see https://www.grid5000.fr/mediawiki/index.php/FAQ#MPI_options_to_use
    mpi_opts = '--mca btl self,sm,tcp'
    return mpi_opts

class mpi_bench(Engine):

    def run(self):
        """Inherited method, put here the code for running the engine"""
        self.define_parameters()
        if self.prepare_bench():
            logger.info('Bench prepared on all frontends')
            self.run_xp()

    def define_parameters(self):
        """Create the iterator on the parameters combinations to be explored"""
        # define the parameters
        self.parameters = {
            'nb_nodes': ['1', '2', '4', '8', '16', '32'],
            'size' : ['B', 'C', 'D'],
            'bench' : ['is', 'ft', 'lu']
        }
        logger.info(self.parameters)
        # define the iterator over the parameters combinations
        self.sweeper = ParamSweeper(os.path.join(self.result_dir, "sweeps"),
                                    sweep(self.parameters))
        logger.info('Number of parameters combinations %s' % len(self.sweeper.get_remaining()))

    def prepare_bench(self):
        """bench configuration and compilation, copy binaries to
        return True if preparation is ok
        """
        

    def run_xp(self):
        """Iterate over the parameters and execute the bench"""
        while len(self.sweeper.get_remaining()) > 0:
            comb = self.sweeper.get_next()
            if comb['n_core'] > get_host_attributes(comb['cluster']+'-1')['architecture']['smt_size'] * self.n_nodes: 
                self.sweeper.skip(comb)
                continue
            logger.info('Processing new combination %s' % (comb,))
            site = get_cluster_site(comb['cluster'])
            jobs = oarsub([(OarSubmission(resources = "{cluster='" + comb['cluster']+"'}/nodes=" + str(self.n_nodes),
                                          job_type = 'allow_classic_ssh', 
                                          walltime ='0:10:00'), 
                            site)])
            if jobs[0][0]:
                try:
                    wait_oar_job_start(*jobs[0])
                    nodes = get_oar_job_nodes(*jobs[0])
                    bench_cmd = 'mpirun -H %s -n %i %s ~/NPB3.3-MPI/bin/lu.%s.%i' % (
                        ",".join([node.address for node in nodes]),
                        comb['n_core'],
                        get_mpi_opts(comb['cluster']),
                        comb['size'],
                        comb['n_core'])
                    lu_bench = SshProcess(bench_cmd, nodes[0])
                    lu_bench.stdout_handlers.append(self.result_dir + '/' + slugify(comb) + '.out')
                    lu_bench.run()
                    if lu_bench.ok:
                        logger.info("comb ok: %s" % (comb,))
                        self.sweeper.done(comb)
                        continue
                finally:
                    oardel(jobs)
            logger.info("comb NOT ok: %s" % (comb,))
            self.sweeper.cancel(comb)

if __name__ == "__main__":
    engine = mpi_bench()
    engine.start()
