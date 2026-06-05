from libhwp import HWPReader


def extract_hwp(path: str) -> str:
    hwp = HWPReader(path)
    return "\n".join(str(p) for p in hwp.find_all("paragraph") if str(p).strip())
