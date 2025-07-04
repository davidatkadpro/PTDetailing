#test.py
from pyrevit import revit, DB
from pyrevit import forms, script
import math
import json

doc = revit.doc


# Future Addition
# - Tendon Grouping
# - Tendon Tagging (Strands/Numbering)

def get_type_by_name(type_name):
	param_type = DB.ElementId(DB.BuiltInParameter.ALL_MODEL_TYPE_NAME)
	f_param = DB.ParameterValueProvider(param_type)
	evaluator = DB.FilterStringEquals()
	f_rule = DB.FilterStringRule(f_param, evaluator, type_name)

	filter_type_name = DB.ElementParameterFilter(f_rule)
	return DB.FilteredElementCollector(doc).WherePasses(filter_type_name).WhereElementIsElementType().FirstElement()

class Tendon:
	def __init__(self, tendon):
		self.ID = int(tendon.get("id"))		
		self.length = self.mtryrd_set( tendon.get("length") )
		self.coordinates = self.set_coordinates(tendon.get("coordinates"))
		self.tendon_type = int(tendon.get("tendon_type"))
		self.strand_type = tendon.get("strand_type")
		self.strand_no = int(tendon.get("strand_no"))
		self.tendon_points = self.set_points(tendon.get("tendon_points"))
	def __str__(self):
		return 'Tendon {}'.format(self.ID)
	def __repr__(self):
		return 'Tendon {}'.format(self.ID)

	def yrdmtr_get(self, numb):
		return (numb * 304.8) / 1000

	def mtryrd_set(self, numb):
		return (1000 * round(numb, 3) ) / 304.8

	def set_coordinates(self, coordinates): #array for start and end point XY
		XYZcoordinates = []
		for xy in coordinates:
			XYZcoordinates.append(
				DB.XYZ(self.mtryrd_set(xy[0]),self.mtryrd_set(xy[1]),0)
			)
		return XYZcoordinates

	def set_points(self, points):
		YrdPoints = []
		for p in points:
			YrdPoints.append([self.mtryrd_set(p[0]), int(p[1] * 1000)]) #only the length needs to be in yards for setout, soffit height is roundedmm
		return YrdPoints


def get_length(para):
	return para * 304.8

def xyz_delta(ref, xyz):
	return DB.XYZ(ref.X + xyz.X, ref.Y + xyz.Y, 0)
	
def do_import():	

	#select file to import

	_path = forms.pick_file(file_ext='json', )
	if not _path:
		doc.exit()
	with open(_path, 'r') as file:
		data = json.load(file)

	#specify coordinates
	point = revit.uidoc.Selection.PickPoint("Pick Tendon 1 Start point")
	

	tendon_set = []
	for st in data:
		tendon_set.append( Tendon(st) )

	detail_component = get_type_by_name("PT - 15.2")

	#line = DB.Line.CreateBound(point1, point2);

	active_view = revit.uidoc.ActiveView
	#ref = DB.Reference(active_view)
	#strct = DB.Structure.StructuralType.NonStructural

	xyz_basepoint = DB.XYZ(point.X - tendon_set[0].coordinates[0].X, point.Y - tendon_set[0].coordinates[0].Y, 0)
	lines = []
	try:
		with revit.Transaction('Create Tendons', show_error_dialog = True):
			for t in tendon_set:
				start_coord = t.coordinates[0]
				end_coord = t.coordinates[1]
				start_xyz_delta = xyz_delta(xyz_basepoint, start_coord)
				end_xyz_delta = xyz_delta(xyz_basepoint, end_coord)

				line = DB.Line.CreateBound(start_xyz_delta, end_xyz_delta)
				print(line)
				detailLine = doc.Create.NewDetailCurve(active_view, line)
				print(detailLine)
				detailLinecurve = detailLine.GeometryCurve
				print(detailLinecurve)
				pt_tendon = doc.Create.NewFamilyInstance(detailLinecurve, detail_component, active_view)

				#change the end stress - current is just default end stress, with PTD data we can add in pan alternative
				end1 = [p for p in pt_tendon.Parameters if p.Definition.Name == "End 1 Display Mode" ][0] #could also use .get_Parameter()
				end1.Set(1)

				#add drape symbols
				end_drape = get_type_by_name("Drape (End)")
				strt_drape = get_type_by_name("Drape (Start)")
				mid_drape = get_type_by_name("Drape (Left Middle)")

				vector_from_pt1_to_pt2 = start_xyz_delta - end_xyz_delta
				angle = vector_from_pt1_to_pt2.AngleTo(DB.XYZ.BasisX)

				# Add point tags to each tendon
				for i, tp in enumerate(t.tendon_points):
					distance, height = tp
					distance_r = distance / t.length

					# check if its the start
					if i == 0:
						point_xyz = start_xyz_delta
						point = doc.Create.NewFamilyInstance(point_xyz, strt_drape, active_view)
						text = [ip for ip in point.Parameters if ip.Definition.Name == "Drape End" ][0]
						text.Set(str(height))
					elif i == len(t.tendon_points)-1: #start and end
						point_xyz = end_xyz_delta
						point = doc.Create.NewFamilyInstance(point_xyz, end_drape, active_view)		
						text = [ip for ip in point.Parameters if ip.Definition.Name == "Drape End" ][0]
						text.Set(str(height))
					else:
						point_xyz = detailLinecurve.Evaluate(distance_r, True);
						point = doc.Create.NewFamilyInstance(point_xyz, mid_drape, active_view)
						text = [ip for ip in point.Parameters if ip.Definition.Name == "Drape" ][0]
						text.Set(str(height))
					ll = DB.Line.CreateBound(point_xyz, point_xyz + DB.XYZ.BasisZ)
					DB.ElementTransformUtils.RotateElement(doc, point.Id, ll, angle - (90 * math.pi /180.0) )

				doc.Delete(detailLine.Id)			
					


	except Exception as ex:
		forms.alert(str(ex), title='Error')		

	


