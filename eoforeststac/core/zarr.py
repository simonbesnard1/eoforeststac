from numcodecs import Blosc

DEFAULT_COMPRESSOR = Blosc(
    cname="zstd",
    clevel=3,
    shuffle=Blosc.BITSHUFFLE,
    blocksize=0,
)