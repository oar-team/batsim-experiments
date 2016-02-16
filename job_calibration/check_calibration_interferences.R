# Reading of files.
# jobs.csv corresponds to batsim output
# expected_runtimes_no_interferences knows the real runtimes of jobs
jobs = read.csv('jobs_interf.csv')
expected = read.csv('expected_runtimes_no_interferences.csv')

# Merge those dataframes
m = merge(jobs, expected, by="jobID")
# Add a new column to know the difference
m["runtime_difference"] <- NA
m$runtime_difference = m$execution_time - m$expected_runtime

thresh = 0.1

# Find jobs whose difference exceeds thresh
j = which(abs(m$runtime_difference) > thresh)

to_calibrate = m[j,]

# Display those jobs
n = to_calibrate[c('jobID', 'profile_name', 'execution_time', 'expected_runtime')]

# Only jobs of size 1
thresh1 = 0.01
j1 = which((m$requested_number_of_processors == 1) & (abs(m$runtime_difference) > thresh1))
to_calibrate1 = m[j1,]
n1 = to_calibrate1[c('jobID', 'profile_name', 'execution_time', 'expected_runtime')]
