from sync_agent.content_engine import SegmentedODFHandler
import datetime
h = SegmentedODFHandler()
d = h.parse(r"D:\PortFiles\NLGFiles\NLGMassFiles\info.odt")
c = h.parse(r"C:\Users\nlgun\PortFiles\NLGFiles\NLGMassFiles\info.odt")
date = datetime.date(2026, 3, 14)
print("D:", d.get(date))
print("C:", c.get(date))