"""
Webscraping for the PaperCut MF system for accessing school printer information.
Only works on school computers (because of the url)
"""

from .session import login, Session
