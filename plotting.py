import holoviews as hv
from holoviews import opts

from LUT import LUT


def CreateWaveformPlot(wave: list[int], label: str):
    plot = hv.Curve(wave, label=label)
    return plot


def CreateFftPlot(fft: dict[str, float]):
    fft_plot = hv.Bars(fft, kdims='frequency', vdims=['amplitude', 'phase']).opts(
        xlabel="Frequency",
        ylabel="Amplitude",
        xlim=(0, max_freq := 50),
        xticks=min(int(max_freq), 50),
        color='phase',
        colorbar=True,
        clabel="Phase"
    )
    return fft_plot


def CreateRegisterTable(lut: LUT):
    table = hv.Table({
        'Register': ["MSLUT[0]", "MSLUT[1]", "MSLUT[2]", "MSLUT[3]", "MSLUT[4]", "MSLUT[5]", "MSLUT[6]", "MSLUT[7]", "MSLUTSEL", "MSLUTSTART"],
        'Value': [hex(mslut) for mslut in lut.mslut] + [hex(lut.mslutsel), hex(lut.mslutstart)]},
        kdims=['Register'], vdims=['Value'])
    return table
