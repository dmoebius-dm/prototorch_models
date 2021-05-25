from importlib.metadata import PackageNotFoundError, version

from . import probabilistic
from .cbc import CBC, ImageCBC
from .glvq import (GLVQ, GLVQ1, GLVQ21, GMLVQ, GRLVQ, LVQMLN, ImageGLVQ,
                   ImageGMLVQ, SiameseGLVQ)
from .lvq import LVQ1, LVQ21, MedianLVQ
from .unsupervised import KNN, NeuralGas
from .vis import *

__version__ = "0.1.7"
