#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai

__license__   = 'GPL v3'
__copyright__ = '2010, Kovid Goyal <kovid@kovidgoyal.net>'
__docformat__ = 'restructuredtext en'

from PyQt4.Qt import QApplication, QIcon

from calibre.gui2.preferences import ConfigWidgetBase, test_widget, \
        CommaSeparatedList
from calibre.gui2.preferences.search_ui import Ui_Form
from calibre.gui2 import config, error_dialog
from calibre.utils.config import prefs

class ConfigWidget(ConfigWidgetBase, Ui_Form):

    def genesis(self, gui):
        self.gui = gui
        db = gui.library_view.model().db
        self.db = db

        r = self.register

        r('search_as_you_type', config)
        r('highlight_search_matches', config)
        r('limit_search_columns', prefs)
        r('limit_search_columns_to', prefs, setting=CommaSeparatedList)
        fl = db.field_metadata.get_search_terms()
        self.opt_limit_search_columns_to.update_items_cache(fl)
        self.clear_history_button.clicked.connect(self.clear_histories)

        self.gst_explanation.setText(_(
    "Grouped search terms are search names that permit a query to automatically "
    "search across more than one column. For example, if you create a grouped "
    "search term 'myseries' with the value 'series, #myseries, #myseries2', "
    "the query 'myseries:adhoc' will find the string 'adhoc' in any of the "
    "columns 'series', '#myseries', and '#myseries2'. Enter the name of the "
    "grouped search term in the drop-down box, enter the list of columns "
    "to search in the value box, then push the Save button. "
    "Notes: You cannot create a search term that is a duplicate of an existing "
    "term or user category. Search terms are forced to lower case; 'MySearch' "
    "and 'mysearch' are the same term."))

        self.gst = db.prefs.get('grouped_search_terms', {})
        self.orig_gst_keys = self.gst.keys()

        del_icon = QIcon(I('trash.png'))
        self.gst_delete_button.setIcon(del_icon)
        fl = []
        for f in db.all_field_keys():
            fm = db.metadata_for_field(f)
            if not fm['search_terms']:
                continue
            if not fm['is_category']:
                continue
            fl.append(f)
        self.gst_value.update_items_cache(fl)
        self.fill_gst_box(select=None)

        self.gst_delete_button.setEnabled(False)
        self.gst_save_button.setEnabled(False)
        self.gst_names.currentIndexChanged[int].connect(self.gst_index_changed)
        self.gst_names.editTextChanged.connect(self.gst_text_changed)
        self.gst_value.textChanged.connect(self.gst_text_changed)
        self.gst_save_button.clicked.connect(self.gst_save_clicked)
        self.gst_delete_button.clicked.connect(self.gst_delete_clicked)
        self.gst_changed = False

        self.muc_explanation.setText(_(
    "Add a grouped search term name to this box to automatically generate "
    "a user category with the name of the search term. The user category will be "
    "populated with all the items in the categories included in the grouped "
    "search term. This permits you to see easily all the category items that "
    "are in the fields contained in the grouped search term. Using the above "
    "'myseries' example, the automatically-generated user category would contain "
    "all the series mentioned in 'series', '#myseries1', and '#myseries2'. This "
    "can be useful to check for duplications or to find which column contains "
    "a particular item."))

        if not db.prefs.get('grouped_search_make_user_categories', None):
            db.prefs.set('grouped_search_make_user_categories', [])
        r('grouped_search_make_user_categories', db.prefs, setting=CommaSeparatedList)
        self.muc_changed = False
        self.opt_grouped_search_make_user_categories.editingFinished.connect(
                                                        self.muc_box_changed)

    def muc_box_changed(self):
        self.muc_changed = True

    def gst_save_clicked(self):
        idx = self.gst_names.currentIndex()
        name = icu_lower(unicode(self.gst_names.currentText()))
        if not name:
            return error_dialog(self.gui, _('Grouped Search Terms'),
                                _('The search term cannot be blank'),
                                show=True)
        if idx != 0:
            orig_name = unicode(self.gst_names.itemData(idx).toString())
        else:
            orig_name = ''
        if name != orig_name:
            if name in self.db.field_metadata.get_search_terms() and \
                    name not in self.orig_gst_keys:
                return error_dialog(self.gui, _('Grouped Search Terms'),
                    _('That name is already used for a column or grouped search term'),
                    show=True)
            if name in [icu_lower(p) for p in self.db.prefs.get('user_categories', {})]:
                return error_dialog(self.gui, _('Grouped Search Terms'),
                    _('That name is already used for user category'),
                    show=True)

        val = [v.strip() for v in unicode(self.gst_value.text()).split(',') if v.strip()]
        if not val:
            return error_dialog(self.gui, _('Grouped Search Terms'),
                _('The value box cannot be empty'), show=True)

        if orig_name and name != orig_name:
            del self.gst[orig_name]
        self.gst_changed = True
        self.gst[name] = val
        self.fill_gst_box(select=name)
        self.changed_signal.emit()

    def gst_delete_clicked(self):
        if self.gst_names.currentIndex() == 0:
            return error_dialog(self.gui, _('Grouped Search Terms'),
                _('The empty grouped search term cannot be deleted'), show=True)
        name = unicode(self.gst_names.currentText())
        if name in self.gst:
            del self.gst[name]
            self.fill_gst_box(select='')
            self.changed_signal.emit()
            self.gst_changed = True

    def fill_gst_box(self, select=None):
        terms = sorted(self.gst.keys())
        self.opt_grouped_search_make_user_categories.update_items_cache(terms)
        self.gst_names.blockSignals(True)
        self.gst_names.clear()
        self.gst_names.addItem('', '')
        for t in terms:
            self.gst_names.addItem(t, t)
        self.gst_names.blockSignals(False)
        if select is not None:
            if select == '':
                self.gst_index_changed(0)
            elif select in terms:
                self.gst_names.setCurrentIndex(self.gst_names.findText(select))

    def gst_text_changed(self):
        self.gst_delete_button.setEnabled(False)
        self.gst_save_button.setEnabled(True)

    def gst_index_changed(self, idx):
        self.gst_delete_button.setEnabled(idx != 0)
        self.gst_save_button.setEnabled(False)
        self.gst_value.blockSignals(True)
        if idx == 0:
            self.gst_value.setText('')
        else:
            name = unicode(self.gst_names.itemData(idx).toString())
            self.gst_value.setText(','.join(self.gst[name]))
        self.gst_value.blockSignals(False)

    def commit(self):
        if self.gst_changed:
            self.db.prefs.set('grouped_search_terms', self.gst)
            self.db.field_metadata.add_grouped_search_terms(self.gst)
        return ConfigWidgetBase.commit(self)

    def refresh_gui(self, gui):
        if self.muc_changed:
            gui.tags_view.set_new_model()
        gui.search.search_as_you_type(config['search_as_you_type'])
        gui.library_view.model().set_highlight_only(config['highlight_search_matches'])
        gui.search.do_search()

    def clear_histories(self, *args):
        for key, val in config.defaults.iteritems():
            if key.endswith('_search_history') and isinstance(val, list):
                config[key] = []
        self.gui.search.clear_history()

if __name__ == '__main__':
    app = QApplication([])
    test_widget('Interface', 'Search')

