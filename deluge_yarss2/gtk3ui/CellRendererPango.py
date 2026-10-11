#
# Copyright (C) 2012-2019 bendikro bro.devel+yarss2@gmail.com
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

from .common import GObject, Gtk, Pango, PangoCairo
from .markup import escape, highlight_match


class CustomAttribute(GObject.GObject):
    def __init__(self, attributes_dict=None):
        super().__init__()
        self.attributes_dict = attributes_dict

    def __str__(self):
        return str(self.attributes_dict)


GObject.type_register(CustomAttribute)


class CellRendererPango(Gtk.CellRendererText):
    __gproperties__ = {
        "custom": (CustomAttribute, "custom", "custom", GObject.ParamFlags.READWRITE),
    }

    property_names = __gproperties__.keys()

    def __init__(self):
        GObject.GObject.__init__(self)
        self.include_color_string = "#5acf36"  # Green
        self.exclude_color_string = "#f31010"  # Red

    def __getattr__(self, name):
        try:
            return self.get_property(name)
        except TypeError:
            raise AttributeError

    def __setattr__(self, name, value):
        try:
            self.set_property(name, value)
        except TypeError:
            self.__dict__[name] = value

    def do_get_property(self, property):
        if property.name not in self.property_names:
            raise TypeError(f"No property named {property.name}")
        return self.__dict__[property.name]

    def do_set_property(self, property, value):
        if property.name not in self.property_names:
            raise TypeError(f"No property named {property.name}")
        self.__dict__[property.name] = value

    def get_text(self):
        value = self.get_property("text")
        return value

    def get_layout(self, widget):
        """Gets the Pango layout used in the cell in a TreeView widget."""
        layout = Pango.Layout(widget.get_pango_context())
        layout.set_width(-1)  # Do not wrap text.
        return layout

    def _build_markup(self, custom_attr):
        text = self.get_text() or ""
        attributes_dict = custom_attr.attributes_dict if custom_attr else None
        if not attributes_dict:
            return escape(text)
        if "regex_exclude_match" in attributes_dict:
            return highlight_match(text, attributes_dict["regex_exclude_match"], self.exclude_color_string)
        if "regex_include_match" in attributes_dict:
            return highlight_match(text, attributes_dict["regex_include_match"], self.include_color_string)
        return escape(text)

    def do_render(self, window, widget, background_area, cell_area, expose_area, flags=None):
        """
        Args:
            window (cairo.Context)
            widget (gi.overrides.Gtk.TreeView)
            background_area (gi.repository.Gdk.Rectangle)
            cell_area (gi.repository.Gdk.Rectangle)
            expose_area (gi.repository.Gtk.CellRendererState)
        """
        cairo_context = window
        layout = self.get_layout(widget)
        custom_attr = self.get_property("custom")
        layout.set_markup(self._build_markup(custom_attr))

        # Vertically align the text
        cell_area.y += 4
        cell_area.x += 1

        cairo_context.move_to(cell_area.x, cell_area.y)
        PangoCairo.show_layout(cairo_context, layout)

    def do_get_size(self, widget, cell_area=None):
        return Gtk.CellRendererText.do_get_size(self, widget, cell_area)


GObject.type_register(CellRendererPango)
