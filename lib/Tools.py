# Structural Section Sizing
from pyrevit import revit, DB, forms

doc = revit.doc

search_terms = ["pt","tendon","post","tensioning"]

def GetTypeName(element):
	return DB.Element.Name.__get__(element)

def GetParaByName(element, name):
	for p in element.Parameters:
		if p.Definition.Name == name:
			return p
	return None
	
def get_type_by_name(type_name):
	param_type = DB.ElementId(DB.BuiltInParameter.ALL_MODEL_TYPE_NAME)
	f_param = DB.ParameterValueProvider(param_type)
	evaluator = DB.FilterStringEquals()
	f_rule = DB.FilterStringRule(f_param, evaluator, type_name)

	filter_type_name = DB.ElementParameterFilter(f_rule)
	return DB.FilteredElementCollector(doc).WherePasses(filter_type_name).WhereElementIsElementType().FirstElement()

def text_has_match(text, item_list):
	tl = text.lower()
	for li in item_list:
		if  li in tl:
			return True
	return False

class TransLength:
	@staticmethod
	def get(Parameter):
		if not Parameter:
			return None
		return Parameter.AsDouble() * 304.8
	@staticmethod
	def set(Parameter):
		if not Parameter:
			return None
		return Parameter / 304.8

class TransText:
	@staticmethod
	def get(Parameter):
		if not Parameter:
			return None
		return Parameter.AsString()

class TransXYZ:
	@staticmethod
	def get(xyz):
		if not xyz:
			return None
		return ( xyz.X * 304.8, xyz.Y * 304.8, xyz.Z * 304.8) 

class MyOption(object):
	def __init__(self, name, state=False):
		self.state = state
		self.name = name
	def __nonzero__(self):
		return self.state
	def __str__(self):
		return self.name

	def __repr__(self):
		return '{}-{}'.format(self.name, self.state)

class BaseCheckBoxItem(object):
	"""Base class for checkbox option wrapping another object."""

	def __init__(self, orig_item):
		"""Initialize the checkbox option and wrap given obj.

		Args:
			orig_item (any): object to wrap (must have name property
							 or be convertable to string with str()
		"""
		self.item = orig_item
		self.state = False

	def __nonzero__(self):
		return self.state

	def __str__(self):
		return self.name or str(self.item)

	@property
	def name(self):
		"""Name property."""
		return getattr(self.item, 'name', '')

	def unwrap(self):
		"""Unwrap and return wrapped object."""
		return self.item


class SelectFromCheckBoxes(forms.TemplateUserInputWindow):
	xaml_source = 'SelectFromCheckboxes.xaml'
	def _setup(self, **kwargs):
		self.hide_element(self.clrsearch_b)
		self.search_tb.Focus()

		self.checked_only = kwargs.get('checked_only', False)
		button_name = kwargs.get('button_name', None)
		if button_name:
			self.select_b.Content = button_name

		self.list_lb.SelectionMode = Controls.SelectionMode.Extended

		self._verify_context()
		self._list_options()

	def _verify_context(self):
		new_context = []
		for item in self._context:
			if not hasattr(item, 'state'):
				new_context.append(BaseCheckBoxItem(item))
			else:
				new_context.append(item)

		self._context = new_context

	def _list_options(self, checkbox_filter=None):
		if checkbox_filter:
			self.checkall_b.Content = 'Check'
			self.uncheckall_b.Content = 'Uncheck'
			self.toggleall_b.Content = 'Toggle'
			checkbox_filter = checkbox_filter.lower()
			self.list_lb.ItemsSource = \
				[checkbox for checkbox in self._context
				 if checkbox_filter in checkbox.name.lower()]
		else:
			self.checkall_b.Content = 'Check All'
			self.uncheckall_b.Content = 'Uncheck All'
			self.toggleall_b.Content = 'Toggle All'
			self.list_lb.ItemsSource = self._context

	def _set_states(self, state=True, flip=False, selected=False):
		all_items = self.list_lb.ItemsSource
		if selected:
			current_list = self.list_lb.SelectedItems
		else:
			current_list = self.list_lb.ItemsSource
		for checkbox in current_list:
			if flip:
				checkbox.state = not checkbox.state
			else:
				checkbox.state = state

		# push list view to redraw
		self.list_lb.ItemsSource = None
		self.list_lb.ItemsSource = all_items

	def toggle_all(self, sender, args):
		"""Handle toggle all button to toggle state of all check boxes."""
		self._set_states(flip=True)

	def check_all(self, sender, args):
		"""Handle check all button to mark all check boxes as checked."""
		self._set_states(state=True)

	def uncheck_all(self, sender, args):
		"""Handle uncheck all button to mark all check boxes as un-checked."""
		self._set_states(state=False)

	def check_selected(self, sender, args):
		"""Mark selected checkboxes as checked."""
		self._set_states(state=True, selected=True)

	def uncheck_selected(self, sender, args):
		"""Mark selected checkboxes as unchecked."""
		self._set_states(state=False, selected=True)

	def button_select(self, sender, args):
		"""Handle select button click."""
		if self.checked_only:
			self.response = [x.item for x in self._context if x.state]
		else:
			self.response = self._context
		self.Close()

	def search_txt_changed(self, sender, args):
		"""Handle text change in search box."""
		if self.search_tb.Text == '':
			self.hide_element(self.clrsearch_b)
		else:
			self.show_element(self.clrsearch_b)

		self._list_options(checkbox_filter=self.search_tb.Text)

	def clear_search(self, sender, args):
		"""Clear search box."""
		self.search_tb.Text = ' '
		self.search_tb.Clear()
		self.search_tb.Focus()

class FormOptions(object):
	def __init__(self, items, defaults=None, search=None, res_defaults=True):
		self.multi 		= True
		self.items 		= items
		self.defaults 	= defaults
		self.search 	= search
		self.res_defaults=res_defaults
		self.set_items 	= None
		self.results 	= None
		# Check if
		if defaults and type(defaults) != list:
			self.multi = False
			self.defaults = [defaults]
	def set_types(self):
		self.set_items = {}
		for ti in self.items:			
			if self.search and not text_has_match(ti.FamilyName, self.search):
				continue
			t_name = GetTypeName(ti)
			name = "{} - {}".format(ti.FamilyName, t_name)
			is_default = False
			if self.defaults and len(self.defaults) > 0:
				for d in self.defaults:
					if d in t_name.lower():
						name = "<<Default>> {}".format(name)
						is_default = True
			self.set_items[name] = [ti, is_default]
		return list(self.set_items)

	def get_types(self, res):
		if not res and self.res_defaults:
			self.results = [self.set_items[r][0] for r in self.set_items if self.set_items[r][1]]
		elif not res:
			self.results = []
		else:
			self.results = [self.set_items[r][0] for r in self.set_items if r in res]
		if not self.multi:
			return self.get_first()
		return self.results

	def get_first(self):
		if len(self.results) > 0:
			return self.results[0]
		return None	