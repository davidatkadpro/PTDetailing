#Tendon.py
#Tendon Class
from pyrevit import revit, DB
from pyrevit import forms

doc = revit.doc
#Tendon Cration
#	- Option 1 - from Instance
#	- Option 2 - from data
class Tendon:
	ID 				= None	
	length 			= None
	start 			= DB.XYZ(0,0,0)
	end 			= DB.XYZ(0,0,0)
	tendon_type 	= None
	strand_type 	= None
	strand_no 		= None
	tendon_points 	= []
	element 		= None
	def __init__(self, **kwargs):
		IsElement = kwargs.get("element", None)
		if IsElement and len(kwargs) == 1:
			self.element = IsElement
			self._init_element()
		HasID = kwargs.get("ID", None)
		if HasID and type(HasID) == int:
			self.ID = kwargs.get("ID")

		if not IsElement and not HasID:
			return False
		
	def __str__(self):
		return 'Tendon {}'.format(self.ID)
	def __repr__(self):
		return 'Tendon {}'.format(self.ID)


	def _init_element(self):
		self.ID = self.element.LookupParameter('PT Tendon Id').AsInteger()				
		self.start = self.element.Location.Curve.GetEndPoint(0)
		self.end = self.element.Location.Curve.GetEndPoint(1)
		self.length = self.start.DistanceTo(self.end)
		self.strand_no = self.element.LookupParameter("PT No. of Strands within Tendon").AsInteger()		
		self.strand_type = self.element.LookupParameter("PT Strand Size").AsDouble()	
		tp = [float(p) for p in self.element.LookupParameter('PT Tendon Data').AsString().split(",")]
		self.tendon_points = [ [round(p,3),int(i)] for p, i in zip(tp[::2], tp[1::2] ) ]


	def yrdmtr_get(self, numb):
		return (numb * 304.8) / 1000

	def mtryrd_set(self, numb):
		return round((1000 * round(numb, 3) ) / 304.8, 3)

	def set_coordinates(self, coordinate): #array for start and end point XY
		return DB.XYZ(self.mtryrd_set(coordinate[0]),self.mtryrd_set(coordinate[1]),0)

	def set_points(self, points):
		YrdPoints = []
		for p in points:
			YrdPoints.append([self.mtryrd_set(p[0]), int(p[1] * 1000)]) #only the length needs to be in yards for setout, soffit height is roundedmm
		return YrdPoints

