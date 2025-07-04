#TendonSet.py

from pyrevit import revit, DB
from pyrevit import forms, script
import math

from Tools import GetTypeName, TransXYZ, GetParaByName, FormOptions

from Tendon import Tendon
doc = revit.doc
uidoc = revit.uidoc
class TendonSet(list):
	def __init__(self, tendons=None):
		self.dependencies = False
		if isinstance(tendons, Tendon):
			self.append(tendons)
		if type(tendons) == list or isinstance(tendons, TendonSet):
			for tendon in tendons:
				if not isinstance(tendon, Tendon):
					continue
				self.append(tendon)

	def first_tendon(self):
		if len(self) > 0:
			return list(self)[0]

		
	def xyz_align(self, ref, xyz):
		return DB.XYZ(ref.X + xyz.X, ref.Y + xyz.Y, 0)

	def prase_data(self, data):
		requirements = ["id","length","coordinates","tendon_type","strand_type","strand_no","tendon_points"]
		try:
			for d in data:
				if d not in requirements:
					print("tendon creation failure: doesnt meet parameter requirements")
					return False
			return Tendon(data)

		except Exception as ex:
			print("tendon creation error:",str(ex))	


	def add_dependencies(self, xyz_delta, tendon_symbol, point_symbols, tag_symbol):
		try:
			self.xyz_delta = xyz_delta
			self.tendon_symbol = tendon_symbol
			
			self.drape_start_symbol = [ds for ds in point_symbols if "start" in GetTypeName(ds).lower()][0]
			self.drape_end_symbol = [de for de in point_symbols if "end" in GetTypeName(de).lower()][0]
			self.drape_mid_symbol =[dm for dm in point_symbols if "middle" in GetTypeName(dm).lower() or "left" in GetTypeName(dm).lower()][0]

			self.tag_symbol = tag_symbol
			self.dependencies = True
			return True
		except Exception as ex:
			print("Failed to load dependencies:", str(ex))	

	def write_tendon_drape(self, tendon):	
		# !!!! Dont Tag if pan within 1000mmm from end !!! - needs to be added
		vector_from_pt1_to_pt2 = tendon.start - tendon.end

		angle = vector_from_pt1_to_pt2.AngleTo(DB.XYZ.BasisX)
		detailLinecurve = tendon.element.Location.Curve
		# Check if its a pan to skip ends
		end1 = GetParaByName(tendon.element, "End 1 Display Mode")

		is_pan = False
		if end1.AsInteger() == 3:
			is_pan = True
		for i, tp in enumerate(tendon.tendon_points):

			distance, height = tp
			distance_r = distance / tendon.length

			if i == 0:
				point_xyz = tendon.start if not is_pan else detailLinecurve.Evaluate( (600/304.8) / tendon.length, True)
				point = doc.Create.NewFamilyInstance(point_xyz, self.drape_start_symbol, uidoc.ActiveView)
				text = [ip for ip in point.Parameters if ip.Definition.Name == "Drape End" ][0]
				text.Set(str(height))
			elif i == len(tendon.tendon_points)-1:
				point_xyz = tendon.end
				point = doc.Create.NewFamilyInstance(point_xyz, self.drape_end_symbol, uidoc.ActiveView)	
				text = [ip for ip in point.Parameters if ip.Definition.Name == "Drape End" ][0]
				text.Set(str(height))
			else:
				if is_pan and distance < (1000/304.8):
					continue
				point_xyz = detailLinecurve.Evaluate(distance_r, True);
				point = doc.Create.NewFamilyInstance(point_xyz, self.drape_mid_symbol, uidoc.ActiveView)
				text = [ip for ip in point.Parameters if ip.Definition.Name == "Drape" ][0]
				text.Set(str(height))

			ll = DB.Line.CreateBound(point_xyz, point_xyz + DB.XYZ.BasisZ)
			
			DB.ElementTransformUtils.RotateElement(doc, point.Id, ll, angle - (90 * math.pi /180.0) )

	def check_grouping(self, last, current):
		if not last:
			return False
		if len(last.tendon_points) != len(current.tendon_points):
			return False
		for i, tp in enumerate(last.tendon_points):
			if i == 0 or i == len(last.tendon_points)-1:
				continue
			ctp = current.tendon_points[i]
			if ctp[0] != tp[0] or ctp[0] != tp[0]:
				return False
		return True

	def write_tendon_tags(self):
		if self.dependencies == False:
			return
		try:
			with revit.Transaction('Create Tendon Tags', show_error_dialog = True):
				box = uidoc.ActiveView.CropBox
				box_center = ((box.Max - box.Min)/2)+box.Min
				for tendon in self:
					tag_end = [None,0,None]

					start_inner = tendon.element.Location.Curve.Evaluate( (2000/304.8) / tendon.length, True)
					start_inner = tendon.start - start_inner
					end_inner = tendon.element.Location.Curve.Evaluate( (tendon.length-(2000/304.8)) / tendon.length, True) 
					end_inner = tendon.end - end_inner
					for te, inn in [[tendon.start,start_inner],[tendon.end,end_inner]]:
						dist = box_center.DistanceTo(te)
						if dist > tag_end[1]:
							tag_end = [te, dist, inn]

					tag_xyz =  tag_end[2]
					tag = DB.IndependentTag.Create(doc,\
							uidoc.ActiveView.Id, \
							DB.Reference(tendon.element), \
							True, \
							DB.TagMode.TM_ADDBY_CATEGORY, \
							DB.TagOrientation.Horizontal, \
							tag_end[0])
					tag.Location.Move( DB.XYZ(tag_xyz.X, tag_xyz.Y, 0 ) )


		except Exception as ex:
			forms.alert(str(ex), title='Error')	

	def write_tendon_drapes(self):
		if self.dependencies == False:
			return
		detail_types =	  DB.FilteredElementCollector(doc)\
							.OfClass(DB.ElementType)\
							.OfCategory(DB.BuiltInCategory.OST_DetailComponents)\
							.ToElements()
		details = FormOptions(detail_types, defaults="Max Centres")
		leader_type = details.get_types( forms.SelectFromList.show(details.set_types(), button_name='Select span component') )

		print(leader_type)
		print(leader_type.FamilyName)
		try:
			with revit.Transaction('Create Tendon Drapes', show_error_dialog = True):
				last = None
				box = uidoc.ActiveView.CropBox
				box_center = ((box.Max - box.Min)/2)+box.Min
				leader = {"count":0,"mid-point":None}
				for tendon in self:
					mid_point = last.element.Location.Curve.Evaluate( 0.5, True) if last else None
					is_match = self.check_grouping(last, tendon)
					grouped =  GetParaByName(tendon.element, "Grouped")					
					if not is_match:
						self.write_tendon_drape(tendon)
						grouped.Set(False)
						if leader["mid-point"]:
							leader, leader_obj = self.end_leader(leader, mid_point,leader_type)
					else:
						if not leader["mid-point"]:
							leader["mid-point"] = mid_point
							leader["count"] = 1
						elif leader["mid-point"]:
							leader["count"] = 1 + leader["count"]

						grouped.Set(True)

					last = tendon
				if leader["mid-point"]:
					leader, leader_obj = self.end_leader(leader, last.element.Location.Curve.Evaluate( 0.5, True),leader_type)
		except Exception as ex:
			forms.alert(str(ex), title='Error')	

	def end_leader(self, leader, mid_point, leader_type):
		line = DB.Line.CreateBound(leader["mid-point"], mid_point)
		detailLine = doc.Create.NewDetailCurve(uidoc.ActiveView, line)
		detailLinecurve = detailLine.GeometryCurve
		leader_obj = doc.Create.NewFamilyInstance(detailLinecurve, leader_type, uidoc.ActiveView)
		distance = leader["mid-point"].DistanceTo(mid_point)
		print(distance, leader["count"])
		cts = GetParaByName(leader_obj, "Centres")
		cts.Set(distance/leader["count"])
		doc.Delete(detailLine.Id)	
		leader["mid-point"] = None
		leader["count"] = 0	
		return [leader, leader_obj] 	

	def write_tendons(self):
		if self.dependencies == False:
			return
		box = uidoc.ActiveView.CropBox
		box_center = ((box.Max - box.Min)/2)+box.Min

		try:
			with revit.Transaction('Create Tendons', show_error_dialog = True):
				for tendon in self:

					tendon.start = self.xyz_align(self.xyz_delta, tendon.start)
					tendon.end = self.xyz_align(self.xyz_delta, tendon.end)

					line = DB.Line.CreateBound(tendon.start, tendon.end)

					detailLine = doc.Create.NewDetailCurve(uidoc.ActiveView, line)

					detailLinecurve = detailLine.GeometryCurve

					tendon.element = doc.Create.NewFamilyInstance(detailLinecurve, self.tendon_symbol, uidoc.ActiveView)

					#store point data
					pointdata = ",".join(["{},{}".format(p[0],p[1]) for p in tendon.tendon_points])
					data = tendon.element.LookupParameter('PT Tendon Data')
					data.Set(pointdata)

					t_id = tendon.element.LookupParameter('PT Tendon Id')
					t_id.Set(tendon.ID)

					strands = tendon.element.LookupParameter("PT No. of Strands within Tendon")
					strands.Set(tendon.strand_no)

					strand_type = tendon.element.LookupParameter("PT Strand Size")
					strand_type.Set(tendon.strand_type)

					#change the end stress - current is just default end stress, with PTD data we can add in pan alternative

					end1 = GetParaByName(tendon.element, "End 1 Display Mode")
					if tendon.tendon_type == 1:
						end1.Set(1)
					else:
						end1.Set(3)
					
					doc.Delete(detailLine.Id)			
				return True	


		except Exception as ex:
			forms.alert(str(ex), title='Error')	
