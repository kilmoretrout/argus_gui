import numpy as np
import pandas

class WandOutputter():
    # name - output tag and location
    # ncams - number of cameras
    # npframes - number of frames in the paired points CSV file
    # pset1 - first set of 3D coordinates from the paired points file
    # pset2 - second set of 3D coordinates from the paired points file
    # pind - set of indices where the 3D coordinates go in the outputted CSV for paired points
    # upset - set of unpaired 3D coordinates
    # nupframes - number of frames in the unpaired points CSV file
    def __init__(self, name, ncams, npframes = None, pset1 = None, pset2 = None, pind = None, upset = None, upind = None, nupframes = None):
        self.name = name
        self.ncams = ncams
        self.npframes = npframes
        self.nupframes = nupframes
        self.pset1 = pset1
        self.pset2 = pset2
        self.pind = pind
        if upind is not None:
            self.nptspframe = len(upind)
        self.upset = upset
        self.upind = upind

    def output(self):
        if self.npframes is not None:
            pout = np.zeros((self.npframes, 6))

            i1 = 0
            i2 = 0
            for k in range(self.npframes):
                if k in self.pind[0]:
                    pout[k,:3] = self.pset1[i1]
                    i1 += 1
                if k in self.pind[1]:
                    pout[k,3:] = self.pset2[i2]
                    i2 += 1

            pout[pout == 0] = np.nan

            dataf = pandas.DataFrame(pout, columns = 'x_1,y_1,z_1,x_2,y_2,z_2'.split(','))
            dataf.to_csv(self.name + '-paired-points-xyz.csv', index = False, na_rep = 'NaN')
            
            # Deprecated code, pandas is way faster than writing the CSV line by line manually
            """
            fo = open(self.name + '-paired-points-xyz.csv', 'wb')
            fo.write('x_1,y_1,z_1,x_2,y_2,z_2\n')
            for k in range(pout.shape[0]):
                l = map(str, pout[k])
                for j in range(len(l)):
                    fo.write(l[j] + ',')
                fo.write('\n')
            fo.close()
            """
        if self.upset is not None:
            upout = np.zeros((self.nupframes, self.nptspframe*3))
            start = 0
            for k in range(self.nptspframe):
                end = start + len(self.upind[k])
                p = self.upset[start:end, :]
                i = 0
                for j in range(self.nupframes):
                    if j in self.upind[k]:
                        upout[j,3*k:(k+1)*3] = p[i]
                        i += 1
                start = end

            upout[upout == 0] = np.nan
            cols = []
            for k in range(int(float(upout.shape[1])/3.)):
                cols = cols + 'x_{0},y_{0},z_{0}'.format(k+1).split(',')
            dataf = pandas.DataFrame(upout, columns = cols)
            dataf.to_csv(self.name + '-unpaired-points-xyz.csv', index = False, na_rep = 'NaN')

            """
            fo = open(self.name + '-unpaired-points-xyz.csv', 'wb')
            fo.write('x_1,y_1,z_1,...\n')
            for k in range(upout.shape[0]):
                l = map(str, upout[k])
                for j in range(len(l)):
                    fo.write(l[j] + ',')
                fo.write('\n')
            fo.close()
            """
