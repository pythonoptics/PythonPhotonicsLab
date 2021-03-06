from spe_loader import SpeFile
from LowLevelModules.GeneralFunctions import voigt_func, voigt_func_2p
from scipy.optimize import curve_fit
from scipy.fftpack import rfft, irfft, fftfreq
import numpy as np
import matplotlib.pyplot as plt


class Spectrum(SpeFile):

    def __init__(self, filename):
        super().__init__(filename)
        self.x = self.wavelength.T
        self.y = self.data[0][0].T / self.exposure_time
        self.y = self.y[:, 0]

    def remove_cosmic_ray(self, n_std=5):
        """n_std for threshold on how many standard deviation from the median to exclude data"""
        idx, = np.where(abs(self.y - np.median(self.y)) > n_std * np.std(self.y))

        if idx.size != 0:
            idx_prev = idx[0] - 1
            idx_next = idx[-1] + 1
            slope = (self.y[idx_next] - self.y[idx_prev]) / (self.x[idx_next] - self.x[idx_prev])
            origin_crossing = self.y[idx_prev] - slope * self.x[idx_prev]
            cts_replace = slope * self.x[idx] + origin_crossing
            y_noise = 0.1 * np.std(self.y) * np.random.normal(size=cts_replace.size)
            self.y[idx] = cts_replace + y_noise

    def remove_etaloning(self, x0, x1='end', sigma=.01, plotplot=False):
        # fourier transform of signal
        f_signal = rfft(self.y)
        freqs = fftfreq(self.y.size, d=self.x[1] - self.x[0])

        # window function to filter out unwanted frequencies
        # NB: using a box for filtering results in ringing effect of the spectrum in real space
        if type(x1) == str:
            x1 = np.abs(np.max(freqs))
        wf1 = 1 / (1 + np.exp(-(freqs - x0) / sigma)) * (1 - 1 / (1 + np.exp(-(freqs - x1) / sigma)))
        wf1 = 1 - wf1 / np.max(wf1)

        cut_f_signal = f_signal * wf1

        cut_signal = irfft(cut_f_signal)
        if plotplot:
            fig = plt.figure(figsize=(10, 3))
            ax1 = fig.add_subplot(121)
            ax1.plot(freqs[freqs >= 0], f_signal[freqs >= 0])
            ax1.plot(freqs[freqs >= 0], cut_f_signal[freqs >= 0])
            plt.xlim([0, 1])
            plt.ylim([-5000, 5000])
            ax2 = fig.add_subplot(122)
            ax2.plot(self.x, self.y)
            ax2.plot(self.x, cut_signal)
        self.y = cut_signal

    @staticmethod
    def calc_peak_separation(lambda1, lambda2):
        e1 = 1241/lambda1
        e2 = 1241/lambda2
        return np.abs(lambda1-lambda2), 1000 * np.abs(e1-e2)

    def fit_2voigt(self, bds):
        popt, pcov = curve_fit(voigt_func_2p, self.x, self.y, bounds=bds)
        print(popt)
        c1f = popt[:4]
        c2f = popt[4:]
        lambda_sep, ener_sep = self.calc_peak_separation(c1f[1], c2f[1])
        print('Peak separation:', np.round(lambda_sep, 2), 'nm.    ', np.round(ener_sep, 2), 'meV.')
        return voigt_func_2p(self.x, *c1f, *c2f), voigt_func(self.x, *c1f), voigt_func(self.x, *c2f)
