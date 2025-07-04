# -*- coding: utf-8 -*-
"""Project Settings dialog for PTDetailing.

Opens a WPF window that lets the user edit project-level settings stored via
`revit_backend.settings` helper.  Runs inside pyRevit (IronPython).
"""

from pyrevit import revit, forms, script
from System.Windows import Window
from System import Uri

from revit_backend import settings  # type: ignore

# ---------------------------------------------------------------------------
# External XAML moved into separate file (settings.xaml) to avoid path-parsing
# issues inside pyRevit when passing literal strings.

# ---------------------------------------------------------------------------
# Window code-behind
# ---------------------------------------------------------------------------

class SettingsWindow(forms.WPFWindow):
    def __init__(self):
        forms.WPFWindow.__init__(self, "settings.xaml")
        self._load_values()
        # attach handlers
        self.OkBtn.Click += self._on_ok

    # --------------------- internal helpers ---------------------
    def _load_values(self):
        data = settings.load()
        # Families
        self.TendonFamilyTb.Text = data.get("tendon_family", "")
        self.LeaderFamilyTb.Text = data.get("leader_family", "")
        self.DrapeFamilyTb.Text = data.get("drape_family", "")
        self.TagFamilyTb.Text = data.get("tag_family", "")
        # Tagging
        self.DrapeTagsCb.IsChecked = bool(data.get("drape_tags", True))
        self.DrapeEndTagsCb.IsChecked = bool(data.get("drape_end_tags", False))
        self.TagStrandsCb.IsChecked = bool(data.get("tag_tendon_strands", True))
        # Grouping
        self.GroupTendonsCb.IsChecked = bool(data.get("group_tendons", True))
        self.CreateDetailGroupCb.IsChecked = bool(data.get("create_detail_group", True))
        self.AngleTolTb.Text = str(data.get("group_angle_tol_deg", "5.0"))
        self.LengthTolTb.Text = str(data.get("group_length_tol_mm", "200"))
        self.SpacingTolTb.Text = str(data.get("group_spacing_tol_mm", "1500"))
        self.ShiftTolTb.Text = str(data.get("group_shift_tol_mm", "600"))
        self.DrapeDistTolTb.Text = str(data.get("group_drape_dist_tol_mm", "200"))
        self.DrapeHeightTolTb.Text = str(data.get("group_drape_height_tol_mm", "5"))
        self.PanStressOffsetTb.Text = str(data.get("pan_stressed_end_offset_mm", "1000"))
        # Snapping
        self.SnapEndsCb.IsChecked = bool(data.get("auto_snap_ends", True))
        self.SnapTolTb.Text = str(data.get("auto_snap_tolerance_mm", "50"))

    def _get_numeric_val(self, textbox, default_val, is_float=False):
        """Safely get numeric value from textbox, fallback to default."""
        try:
            val_type = float if is_float else int
            return val_type(textbox.Text)
        except (ValueError, TypeError):
            return default_val

    def _gather_values(self):
        return {
            "tendon_family": self.TendonFamilyTb.Text.strip(),
            "leader_family": self.LeaderFamilyTb.Text.strip(),
            "drape_family": self.DrapeFamilyTb.Text.strip(),
            "tag_family": self.TagFamilyTb.Text.strip(),
            # Tagging
            "drape_tags": bool(self.DrapeTagsCb.IsChecked),
            "drape_end_tags": bool(self.DrapeEndTagsCb.IsChecked),
            "tag_tendon_strands": bool(self.TagStrandsCb.IsChecked),
            # Grouping
            "group_tendons": bool(self.GroupTendonsCb.IsChecked),
            "create_detail_group": bool(self.CreateDetailGroupCb.IsChecked),
            "group_angle_tol_deg": self._get_numeric_val(self.AngleTolTb, 5.0, is_float=True),
            "group_length_tol_mm": self._get_numeric_val(self.LengthTolTb, 200),
            "group_spacing_tol_mm": self._get_numeric_val(self.SpacingTolTb, 1500),
            "group_shift_tol_mm": self._get_numeric_val(self.ShiftTolTb, 600),
            "group_drape_dist_tol_mm": self._get_numeric_val(self.DrapeDistTolTb, 200),
            "group_drape_height_tol_mm": self._get_numeric_val(self.DrapeHeightTolTb, 5),
            "pan_stressed_end_offset_mm": self._get_numeric_val(self.PanStressOffsetTb, 1000),
            # Snapping
            "auto_snap_ends": bool(self.SnapEndsCb.IsChecked),
            "auto_snap_tolerance_mm": self._get_numeric_val(self.SnapTolTb, 50),
        }

    # --------------------- event handlers -----------------------
    def _on_ok(self, sender, args):
        data = self._gather_values()
        settings.save(data)
        self.Close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    SettingsWindow().show_dialog()


if __name__ == "__main__":
    main() 