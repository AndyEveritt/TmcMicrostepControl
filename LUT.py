from typing import Callable
import numpy as np
from scipy.fft import fft


class LUT:
    def __init__(self):
        self.mslut: list[int] = None
        self.mslutsel: int = None
        self.mslutstart: int = None
        self.W = [0, 0, 0, 0]
        self.X = [0, 0, 0, 256]

    @staticmethod
    def CreateFromRegisters(mslut: list[int], mslutsel: int, mslutstart: int):
        lut = LUT()
        lut.mslut = mslut
        lut.mslutsel = mslutsel
        lut.mslutstart = mslutstart

        lut.CalculateSegmentation()
        return lut

    @staticmethod
    def CreateFromFunction(waveform_func: Callable[[int], float], amplitude_scaler: int = 248, offset: int = 0):
        microsteps = 256

        lut = LUT()

        values = np.zeros(microsteps, dtype=int)
        for i in range(microsteps):
            values[i] = int((waveform_func(i) * amplitude_scaler) + offset + 0.5)

        differences = np.zeros(microsteps, dtype=int)
        for i in range(microsteps - 1):
            differences[i] = values[i+1] - values[i]

        w = [0] * 4
        x = [0] * 4

        w_index = 0
        x_index = 0

        offs_bits = np.zeros(microsteps, dtype=int)
        seg_differences = []

        for i in range(microsteps):
            if (len(set(seg_differences + [differences[i]])) <= 2) and i < microsteps - 1:
                seg_differences.append(differences[i])
                continue

            seg_base_inc = min(seg_differences)

            if seg_base_inc > 2 or seg_base_inc < -1:
                raise ValueError("Invalid segment base inclination")

            if (x_index > 2 or w_index > 3):
                raise ValueError("Can not fit function")

            w[w_index] = seg_base_inc + 1

            for j, diff in enumerate(seg_differences):
                offs_bit = 0 if seg_base_inc == diff else 1
                offs_bits[j + x[max(0, x_index-1)]] = offs_bit

            x[x_index] = i if i < microsteps - 1 else microsteps
            w_index += 1
            x_index += 1

            seg_differences = [differences[i]]

        while x_index < len(x):
            x[x_index] = 256
            x_index += 1

        lut.W = w
        lut.X = x

        msluts = []
        for reg in range(8):
            mslut = 0
            for bit in range(32):
                mslut |= offs_bits[reg * 32 + bit] << bit

            msluts.append(mslut)

        lut.mslut = msluts
        lut.mslutstart = values[0] | (values[-1] << 16)
        lut.mslutsel = (w[0]) | (w[1] << 2) | (w[2] << 4) | (w[3] << 6) | (x[0] << 8) | (x[1] << 16) | (x[2] << 24)

        return lut

    def CalculateSegmentation(self):
        for i in range(4):
            self.W[i] = (self.mslutsel >> i*2) & 0x03

        for i in range(3):
            self.X[i] = (self.mslutsel >> (i*8 + 8)) & 0xFF

    def GetIncrement(self, pos: int):
        if pos < 0 or pos > 255:
            raise IndexError("invalid position")

        mslut_index = pos % 32
        mslut = self.mslut[pos // 32]

        for i in range(4):
            if (pos < self.X[i]):
                return -1 + self.W[i] + (1 if mslut & (1 << mslut_index) > 0 else 0)

        raise ValueError("Shouldn't be able to get here")

    def GetWaveform(self):
        # First quadrant
        wave = [self.mslutstart & 0xFF]
        for i in range(255):
            wave.append(wave[i] + self.GetIncrement(i))

        # Second quadrant
        for i in range(256):
            wave.append(wave[255 - i])

        # # Second half
        for i in range(256*2):
            wave.append(2*(self.mslutstart & 0xFF) - wave[i])

        return wave

    def GetFFT(self, wave: list[int] = None):
        if wave is None:
            wave = self.GetWaveform()

        t = np.arange(1024)
        x = np.sin(t * 2 * np.pi / 256)

        sr = 1024

        X = fft(wave)
        N = len(X)
        n = np.arange(N)
        T = N/sr
        freq = n/T

        return (freq, np.abs(X) * 2 / 1024)
