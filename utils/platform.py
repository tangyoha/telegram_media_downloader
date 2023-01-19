"""for package download"""

import platform

# def get_platform() -> str:
#     """Get platform title
#     Returns
#     -------
#     str
#         window amd64 return "windows-amd64"
#     """
#     sys_platform = platform.system().lower()
#     platform_str: str = sys_platform
#     if "macos" in sys_platform:
#         platform_str = "osx"

#     machine = platform.machine().lower()

#     if "i386" in machine:
#         platform_str += "-386"
#     else:
#         platform_str += "-" + machine

#     return platform_str


def get_exe_ext() -> str:
    """Get exe ext
    Returns
    str
        if in window then return "exe" other return ""
    """
    if "windows" in platform.system().lower():
        return ".exe"
    return ""
