# -*- coding: utf-8 -*-
"""
OnionShare | https://onionshare.org/

Copyright (C) 2017 Micah Lee <micah@micahflee.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import os
from PyQt5 import QtCore, QtWidgets, QtGui
from .alert import Alert

from onionshare import strings, common

class DropHereLabel(QtWidgets.QLabel):
    """
    When there are no files or folders in the FileList yet, display the
    'drop files here' message and graphic.
    """
    def __init__(self, parent, image=False):
        self.parent = parent
        super(DropHereLabel, self).__init__(parent=parent)
        self.setAcceptDrops(True)
        self.setAlignment(QtCore.Qt.AlignCenter)

        if image:
            self.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage(common.get_resource_path('images/logo_transparent.png'))))
        else:
            self.setText(strings._('gui_drag_and_drop', True))
            self.setStyleSheet('color: #999999;')

        self.hide()

    def dragEnterEvent(self, event):
        self.parent.drop_here_image.hide()
        self.parent.drop_here_text.hide()
        event.accept()


class DropCountLabel(QtWidgets.QLabel):
    """
    While dragging files over the FileList, this counter displays the
    number of files you're dragging.
    """
    def __init__(self, parent):
        self.parent = parent
        super(DropCountLabel, self).__init__(parent=parent)
        self.setAcceptDrops(True)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setText(strings._('gui_drag_and_drop', True))
        self.setStyleSheet('color: #ffffff; background-color: #f44449; font-weight: bold; padding: 5px 10px; border-radius: 10px;')
        self.hide()

    def dragEnterEvent(self, event):
        self.hide()
        event.accept()


class FileList(QtWidgets.QListWidget):
    """
    The list of files and folders in the GUI.
    """
    files_dropped = QtCore.pyqtSignal()
    files_updated = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(FileList, self).__init__(parent)
        self.setAcceptDrops(True)
        self.setIconSize(QtCore.QSize(32, 32))
        self.setSortingEnabled(True)
        self.setMinimumHeight(200)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.filenames = []

        self.drop_here_image = DropHereLabel(self, True)
        self.drop_here_text = DropHereLabel(self, False)
        self.drop_count = DropCountLabel(self)
        self.resizeEvent(None)

    def update(self):
        """
        Update the GUI elements based on the current state.
        """
        # file list should have a background image if empty
        if len(self.filenames) == 0:
            self.drop_here_image.show()
            self.drop_here_text.show()
        else:
            self.drop_here_image.hide()
            self.drop_here_text.hide()

    def server_started(self):
        """
        Update the GUI when the server starts, by hiding delete buttons.
        """
        self.setAcceptDrops(False)
        self.setCurrentItem(None)
        self.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        for index in range(self.count()):
            self.item(index).item_button.hide()

    def server_stopped(self):
        """
        Update the GUI when the server stops, by showing delete buttons.
        """
        self.setAcceptDrops(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        for index in range(self.count()):
            self.item(index).item_button.show()

    def resizeEvent(self, event):
        """
        When the widget is resized, resize the drop files image and text.
        """
        offset = 70
        self.drop_here_image.setGeometry(0, 0, self.width(), self.height() - offset)
        self.drop_here_text.setGeometry(0, offset, self.width(), self.height() - offset)

        if self.count() > 0:
            # Add and delete an empty item, to force all items to get redrawn
            # This is ugly, but the only way I could figure out how to proceed
            item = QtWidgets.QListWidgetItem('fake item')
            self.addItem(item)
            self.takeItem(self.row(item))
            self.update()

    def dragEnterEvent(self, event):
        """
        dragEnterEvent for dragging files and directories into the widget.
        """
        if event.mimeData().hasUrls:
            self.setStyleSheet('FileList { border: 3px solid #538ad0; }')
            count = len(event.mimeData().urls())
            self.drop_count.setText('+{}'.format(count))

            self.drop_count.setGeometry(self.width() - 60, self.height() - 40, 50, 30)
            self.drop_count.show()
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """
        dragLeaveEvent for dragging files and directories into the widget.
        """
        self.setStyleSheet('FileList { border: none; }')
        self.drop_count.hide()
        event.accept()
        self.update()

    def dragMoveEvent(self, event):
        """
        dragMoveEvent for dragging files and directories into the widget.
        """
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """
        dropEvent for dragging files and directories into the widget.
        """
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            for url in event.mimeData().urls():
                filename = str(url.toLocalFile())
                self.add_file(filename)
        else:
            event.ignore()

        self.setStyleSheet('border: none;')
        self.drop_count.hide()

        self.files_dropped.emit()

    def add_file(self, filename):
        """
        Add a file or directory to this widget.
        """
        if filename not in self.filenames:
            if not os.access(filename, os.R_OK):
                Alert(strings._("not_a_readable_file", True).format(filename))
                return

            self.filenames.append(filename)
            # Re-sort the list internally
            self.filenames.sort()

            fileinfo = QtCore.QFileInfo(filename)
            basename = os.path.basename(filename.rstrip('/'))
            ip = QtWidgets.QFileIconProvider()
            icon = ip.icon(fileinfo)

            if os.path.isfile(filename):
                size_bytes = fileinfo.size()
                size_readable = common.human_readable_filesize(size_bytes)
            else:
                size_bytes = common.dir_size(filename)
                size_readable = common.human_readable_filesize(size_bytes)
            item_name = '{0:s} ({1:s})'.format(basename, size_readable)

            # Create a new item
            item = QtWidgets.QListWidgetItem(item_name)
            item.setToolTip(size_readable)
            item.setIcon(icon)
            item.size_bytes = size_bytes

            # Item's delete button
            def delete_item():
                itemrow = self.row(item)
                self.filenames.pop(itemrow)
                self.takeItem(itemrow)
                self.files_updated.emit()

            item.item_button = QtWidgets.QPushButton()
            item.item_button.setDefault(False)
            item.item_button.setFlat(True)
            item.item_button.setIcon( QtGui.QIcon(common.get_resource_path('images/file_delete.png')) )
            item.item_button.clicked.connect(delete_item)

            # Create an item widget to display on the item
            item_widget_layout = QtWidgets.QHBoxLayout()
            item_widget_layout.addStretch()
            item_widget_layout.addWidget(item.item_button)
            item_widget = QtWidgets.QWidget()
            item_widget.setLayout(item_widget_layout)

            self.addItem(item)
            self.setItemWidget(item, item_widget)

            self.files_updated.emit()


class FileSelection(QtWidgets.QVBoxLayout):
    """
    The list of files and folders in the GUI, as well as buttons to add and
    delete the files and folders.
    """
    def __init__(self):
        super(FileSelection, self).__init__()
        self.server_on = False

        # Info label
        self.info_label = QtWidgets.QLabel()
        self.info_label.setStyleSheet('QLabel { font-size: 12px; color: #666666; }')

        # File list
        self.file_list = FileList()
        self.file_list.currentItemChanged.connect(self.update)
        self.file_list.files_dropped.connect(self.update)
        self.file_list.files_updated.connect(self.update)

        # Buttons
        self.add_button = QtWidgets.QPushButton(strings._('gui_add', True))
        self.add_button.clicked.connect(self.add)
        self.delete_button = QtWidgets.QPushButton(strings._('gui_delete', True))
        self.delete_button.clicked.connect(self.delete)
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.delete_button)

        # Add the widgets
        self.addWidget(self.info_label)
        self.addWidget(self.file_list)
        self.addLayout(button_layout)

        self.update()

    def update(self):
        """
        Update the GUI elements based on the current state.
        """
        # Update the info label
        file_count = self.file_list.count()
        if file_count == 0:
            self.info_label.hide()
        else:
            total_size_bytes = 0
            for index in range(self.file_list.count()):
                item = self.file_list.item(index)
                total_size_bytes += item.size_bytes
            total_size_readable = common.human_readable_filesize(total_size_bytes)

            self.info_label.setText(strings._('gui_file_info', True).format(file_count, total_size_readable))
            self.info_label.show()

        # All buttons should be hidden if the server is on
        if self.server_on:
            self.add_button.hide()
            self.delete_button.hide()
        else:
            self.add_button.show()

            # Delete button should be hidden if item isn't selected
            current_item = self.file_list.currentItem()
            if not current_item:
                self.delete_button.hide()
            else:
                self.delete_button.show()

        # Update the file list
        self.file_list.update()

    def add(self):
        """
        Add button clicked.
        """
        file_dialog = FileDialog(caption=strings._('gui_choose_items', True))
        if file_dialog.exec_() == QtWidgets.QDialog.Accepted:
            for filename in file_dialog.selectedFiles():
                self.file_list.add_file(filename)

        self.file_list.setCurrentItem(None)
        self.update()

    def delete(self):
        """
        Delete button clicked
        """
        selected = self.file_list.selectedItems()
        for item in selected:
            itemrow = self.file_list.row(item)
            self.file_list.filenames.pop(itemrow)
            self.file_list.takeItem(itemrow)
        self.file_list.files_updated.emit()

        self.file_list.setCurrentItem(None)
        self.update()

    def server_started(self):
        """
        Gets called when the server starts.
        """
        self.server_on = True
        self.file_list.server_started()
        self.update()

    def server_stopped(self):
        """
        Gets called when the server stops.
        """
        self.server_on = False
        self.file_list.server_stopped()
        self.update()

    def get_num_files(self):
        """
        Returns the total number of files and folders in the list.
        """
        return len(self.file_list.filenames)

    def setFocus(self):
        """
        Set the Qt app focus on the file selection box.
        """
        self.file_list.setFocus()

class FileDialog(QtWidgets.QFileDialog):
    """
    Overridden version of QFileDialog which allows us to select
    folders as well as, or instead of, files.
    """
    def __init__(self, *args, **kwargs):
        QtWidgets.QFileDialog.__init__(self, *args, **kwargs)
        self.setOption(self.DontUseNativeDialog, True)
        self.setOption(self.ReadOnly, True)
        self.setOption(self.ShowDirsOnly, False)
        self.setFileMode(self.ExistingFiles)
        tree_view = self.findChild(QtWidgets.QTreeView)
        tree_view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        list_view = self.findChild(QtWidgets.QListView, "listView")
        list_view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

    def accept(self):
        QtWidgets.QDialog.accept(self)
