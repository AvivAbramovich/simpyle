from dataclasses import dataclass
from typing import Dict


@dataclass
class Test:
    alert: Dict
    src_fv: Dict
    dst_fv: Dict

