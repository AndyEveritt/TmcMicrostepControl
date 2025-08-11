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
    def CreateFromWave(wave: list[int], first_quadrant_microsteps: int = 256):
        """
        Create a Look-Up Table (LUT) object from a given waveform.

        The function takes a list of integer values representing the waveform and an optional parameter
        for the number of microsteps. It calculates the Look-Up Table (LUT) parameters and returns a new
        LUT object.

        Parameters:
        - wave (list[int]): A list of integer values representing the waveform.
        - microsteps (int): The number of microsteps for the first quadrant of the waveform. Default is 256.

        Returns:
        - LUT: A new Look-Up Table object.

        Raises:
        - ValueError: If the number of microsteps is greater than the length of the waveform.
        """
        if (first_quadrant_microsteps > len(wave)):
            raise ValueError(f"Wave does not have enough values")

        lut = LUT()

        values = wave[0:first_quadrant_microsteps]

        differences = np.zeros(first_quadrant_microsteps, dtype=int)
        for i in range(first_quadrant_microsteps - 1):
            differences[i] = values[i+1] - values[i]

        w = [0] * 4
        x = [0] * 4

        w_index = 0
        x_index = 0

        offs_bits = np.zeros(first_quadrant_microsteps, dtype=int)
        seg_differences = []

        for i in range(first_quadrant_microsteps):
            if (len(set(seg_differences + [differences[i]])) <= 2) and i < first_quadrant_microsteps - 1:
                seg_differences.append(differences[i])
                continue

            if (i == first_quadrant_microsteps - 1):
                seg_differences.append(differences[i])

            seg_base_inc = min(seg_differences)

            if seg_base_inc > 2 or seg_base_inc < -1:
                raise ValueError("Invalid segment base inclination")

            if ((x_index > 2 or w_index > 3) and (i < first_quadrant_microsteps - 1)):
                raise ValueError("Can not fit function")

            if (w_index <= 3):
                w[w_index] = seg_base_inc + 1

            for j, diff in enumerate(seg_differences):
                offs_bit = 0 if seg_base_inc == diff else 1
                offs_bits[j + x[max(0, x_index-1)]] = offs_bit

            if (x_index <= 2):
                x[x_index] = i
            w_index += 1
            x_index += 1

            seg_differences = [differences[i]]

        while x_index < len(x):
            x[x_index] = 255
            x_index += 1

        lastW = differences[first_quadrant_microsteps - 1] - offs_bits[first_quadrant_microsteps - 1] + 1
        while w_index < 4:
            w[w_index] = lastW
            w_index += 1

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

    @staticmethod
    def CreateFromFunction(waveform_func: Callable[[int], float], amplitude_scaler: int = 248, offset: int = 0):
        microsteps = 256

        values = np.zeros(microsteps, dtype=int)
        for i in range(microsteps):
            values[i] = int((waveform_func(i) * amplitude_scaler) + offset + 0.5)

        return LUT.CreateFromWave(values, microsteps)

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
            if (pos >= self.X[2]):
                return -1 + self.W[3] + (1 if mslut & (1 << mslut_index) > 0 else 0)

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

        return CalculateFFT(wave)


def CalculateFFT(wave: list[int | float]) -> dict[str, float]:

    sr = len(wave)

    X = fft(wave)
    N = len(X)
    n = np.arange(N)
    T = N/sr
    freq = n/T

    return {
        'frequency': freq,
        'amplitude': np.abs(X) * 2 / sr,
        'phase': np.angle(X) + np.pi / 2
    }
