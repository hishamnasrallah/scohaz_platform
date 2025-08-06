# File: add_all_widget_mappings.py
# Run this to add ALL widget mappings with complete property support

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scohaz_platform.settings')
django.setup()

from builder.models import WidgetMapping

# Complete list of all widget mappings with full property support
all_widget_mappings = [
    # Layout Widgets
    {
        'ui_type': 'container',
        'flutter_widget': 'Container',
        'properties_mapping': {
            'width': 'width: {{value}}.0',
            'height': 'height: {{value}}.0',
            'color': 'color: {{value}}',
            'padding': 'padding: {{value}}',
            'margin': 'margin: {{value}}',
            'alignment': 'alignment: {{value}}',
            'decoration': 'decoration: BoxDecoration({{value}})',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'column',
        'flutter_widget': 'Column',
        'properties_mapping': {
            'mainAxisAlignment': 'mainAxisAlignment: {{value}}',
            'crossAxisAlignment': 'crossAxisAlignment: {{value}}',
            'mainAxisSize': 'mainAxisSize: MainAxisSize.{{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'row',
        'flutter_widget': 'Row',
        'properties_mapping': {
            'mainAxisAlignment': 'mainAxisAlignment: {{value}}',
            'crossAxisAlignment': 'crossAxisAlignment: {{value}}',
            'mainAxisSize': 'mainAxisSize: MainAxisSize.{{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'stack',
        'flutter_widget': 'Stack',
        'properties_mapping': {
            'alignment': 'alignment: {{value}}',
            'fit': 'fit: StackFit.{{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'center',
        'flutter_widget': 'Center',
        'properties_mapping': {
            'widthFactor': 'widthFactor: {{value}}',
            'heightFactor': 'heightFactor: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'padding',
        'flutter_widget': 'Padding',
        'properties_mapping': {
            'padding': 'padding: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'expanded',
        'flutter_widget': 'Expanded',
        'properties_mapping': {
            'flex': 'flex: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'flexible',
        'flutter_widget': 'Flexible',
        'properties_mapping': {
            'flex': 'flex: {{value}}',
            'fit': 'fit: FlexFit.{{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'wrap',
        'flutter_widget': 'Wrap',
        'properties_mapping': {
            'direction': 'direction: Axis.{{value}}',
            'alignment': 'alignment: WrapAlignment.{{value}}',
            'spacing': 'spacing: {{value}}.0',
            'runSpacing': 'runSpacing: {{value}}.0',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'listview',
        'flutter_widget': 'ListView',
        'properties_mapping': {
            'scrollDirection': 'scrollDirection: Axis.{{value}}',
            'shrinkWrap': 'shrinkWrap: {{value}}',
            'physics': 'physics: {{value}}',
            'padding': 'padding: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'gridview',
        'flutter_widget': 'GridView.count',
        'properties_mapping': {
            'crossAxisCount': 'crossAxisCount: {{value}}',
            'mainAxisSpacing': 'mainAxisSpacing: {{value}}.0',
            'crossAxisSpacing': 'crossAxisSpacing: {{value}}.0',
            'childAspectRatio': 'childAspectRatio: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'sizedbox',
        'flutter_widget': 'SizedBox',
        'properties_mapping': {
            'width': 'width: {{value}}.0',
            'height': 'height: {{value}}.0',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'aspectratio',
        'flutter_widget': 'AspectRatio',
        'properties_mapping': {
            'aspectRatio': 'aspectRatio: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'fractionallysizedbox',
        'flutter_widget': 'FractionallySizedBox',
        'properties_mapping': {
            'widthFactor': 'widthFactor: {{value}}',
            'heightFactor': 'heightFactor: {{value}}',
            'alignment': 'alignment: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },

    # Display Widgets
    {
        'ui_type': 'text',
        'flutter_widget': 'Text',
        'properties_mapping': {
            'text': '{{value}}',
            'style': 'style: {{value}}',
            'textAlign': 'textAlign: {{value}}',
            'overflow': 'overflow: TextOverflow.{{value}}',
            'maxLines': 'maxLines: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'richtext',
        'flutter_widget': 'RichText',
        'properties_mapping': {
            'text': 'text: {{value}}',
            'textAlign': 'textAlign: {{value}}',
            'overflow': 'overflow: TextOverflow.{{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'image',
        'flutter_widget': 'Image',
        'properties_mapping': {
            'source': 'Image.network({{value}})',
            'width': 'width: {{value}}.0',
            'height': 'height: {{value}}.0',
            'fit': 'fit: BoxFit.{{value}}',
            'alignment': 'alignment: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'icon',
        'flutter_widget': 'Icon',
        'properties_mapping': {
            'icon': 'Icons.{{value}}',
            'size': 'size: {{value}}.0',
            'color': 'color: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'circularprogressindicator',
        'flutter_widget': 'CircularProgressIndicator',
        'properties_mapping': {
            'value': 'value: {{value}}',
            'backgroundColor': 'backgroundColor: {{value}}',
            'color': 'color: {{value}}',
            'strokeWidth': 'strokeWidth: {{value}}.0',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'linearprogressindicator',
        'flutter_widget': 'LinearProgressIndicator',
        'properties_mapping': {
            'value': 'value: {{value}}',
            'backgroundColor': 'backgroundColor: {{value}}',
            'color': 'color: {{value}}',
            'minHeight': 'minHeight: {{value}}.0',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'divider',
        'flutter_widget': 'Divider',
        'properties_mapping': {
            'height': 'height: {{value}}.0',
            'thickness': 'thickness: {{value}}.0',
            'color': 'color: {{value}}',
            'indent': 'indent: {{value}}.0',
            'endIndent': 'endIndent: {{value}}.0',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'chip',
        'flutter_widget': 'Chip',
        'properties_mapping': {
            'label': 'label: Text({{value}})',
            'avatar': 'avatar: {{value}}',
            'backgroundColor': 'backgroundColor: {{value}}',
            'padding': 'padding: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'circleavatar',
        'flutter_widget': 'CircleAvatar',
        'properties_mapping': {
            'radius': 'radius: {{value}}.0',
            'backgroundColor': 'backgroundColor: {{value}}',
            'backgroundImage': 'backgroundImage: NetworkImage({{value}})',
            'child': 'child: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },

    # Input Widgets
    {
        'ui_type': 'button',
        'flutter_widget': 'ElevatedButton',
        'properties_mapping': {
            'onPressed': 'onPressed: {{value}}',
            'child': 'child: Text({{value}})',
            'style': 'style: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'textbutton',
        'flutter_widget': 'TextButton',
        'properties_mapping': {
            'onPressed': 'onPressed: {{value}}',
            'child': 'child: Text({{value}})',
            'style': 'style: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'outlinedbutton',
        'flutter_widget': 'OutlinedButton',
        'properties_mapping': {
            'onPressed': 'onPressed: {{value}}',
            'child': 'child: Text({{value}})',
            'style': 'style: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'iconbutton',
        'flutter_widget': 'IconButton',
        'properties_mapping': {
            'icon': 'icon: Icon(Icons.{{value}})',
            'onPressed': 'onPressed: {{value}}',
            'color': 'color: {{value}}',
            'iconSize': 'iconSize: {{value}}.0',
            'padding': 'padding: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'floatingactionbutton',
        'flutter_widget': 'FloatingActionButton',
        'properties_mapping': {
            'onPressed': 'onPressed: {{value}}',
            'child': 'child: Icon(Icons.{{value}})',
            'backgroundColor': 'backgroundColor: {{value}}',
            'mini': 'mini: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'textfield',
        'flutter_widget': 'TextField',
        'properties_mapping': {
            'hintText': 'decoration: InputDecoration(hintText: {{value}})',
            'labelText': 'decoration: InputDecoration(labelText: {{value}})',
            'controller': 'controller: {{value}}',
            'obscureText': 'obscureText: {{value}}',
            'keyboardType': 'keyboardType: TextInputType.{{value}}',
            'maxLines': 'maxLines: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'textformfield',
        'flutter_widget': 'TextFormField',
        'properties_mapping': {
            'hintText': 'decoration: InputDecoration(hintText: {{value}})',
            'labelText': 'decoration: InputDecoration(labelText: {{value}})',
            'validator': 'validator: {{value}}',
            'obscureText': 'obscureText: {{value}}',
            'keyboardType': 'keyboardType: TextInputType.{{value}}',
            'maxLines': 'maxLines: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'checkbox',
        'flutter_widget': 'Checkbox',
        'properties_mapping': {
            'value': 'value: {{value}}',
            'onChanged': 'onChanged: {{value}}',
            'activeColor': 'activeColor: {{value}}',
            'checkColor': 'checkColor: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'switch',
        'flutter_widget': 'Switch',
        'properties_mapping': {
            'value': 'value: {{value}}',
            'onChanged': 'onChanged: {{value}}',
            'activeColor': 'activeColor: {{value}}',
            'activeTrackColor': 'activeTrackColor: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'radio',
        'flutter_widget': 'Radio',
        'properties_mapping': {
            'value': 'value: {{value}}',
            'groupValue': 'groupValue: {{value}}',
            'onChanged': 'onChanged: {{value}}',
            'activeColor': 'activeColor: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'slider',
        'flutter_widget': 'Slider',
        'properties_mapping': {
            'value': 'value: {{value}}',
            'onChanged': 'onChanged: {{value}}',
            'min': 'min: {{value}}.0',
            'max': 'max: {{value}}.0',
            'divisions': 'divisions: {{value}}',
            'activeColor': 'activeColor: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'dropdown',
        'flutter_widget': 'DropdownButton',
        'properties_mapping': {
            'value': 'value: {{value}}',
            'items': 'items: {{value}}',
            'onChanged': 'onChanged: {{value}}',
            'hint': 'hint: Text({{value}})',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },

    # Material Design Widgets
    {
        'ui_type': 'card',
        'flutter_widget': 'Card',
        'properties_mapping': {
            'elevation': 'elevation: {{value}}.0',
            'color': 'color: {{value}}',
            'margin': 'margin: {{value}}',
            'shape': 'shape: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'listtile',
        'flutter_widget': 'ListTile',
        'properties_mapping': {
            'title': 'title: Text({{value}})',
            'subtitle': 'subtitle: Text({{value}})',
            'leading': 'leading: {{value}}',
            'trailing': 'trailing: {{value}}',
            'onTap': 'onTap: {{value}}',
            'dense': 'dense: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'appbar',
        'flutter_widget': 'AppBar',
        'properties_mapping': {
            'title': 'title: Text({{value}})',
            'backgroundColor': 'backgroundColor: {{value}}',
            'elevation': 'elevation: {{value}}.0',
            'centerTitle': 'centerTitle: {{value}}',
            'actions': 'actions: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'drawer',
        'flutter_widget': 'Drawer',
        'properties_mapping': {
            'elevation': 'elevation: {{value}}.0',
            'width': 'width: {{value}}.0',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'bottomnavigationbar',
        'flutter_widget': 'BottomNavigationBar',
        'properties_mapping': {
            'items': 'items: {{value}}',
            'currentIndex': 'currentIndex: {{value}}',
            'onTap': 'onTap: {{value}}',
            'backgroundColor': 'backgroundColor: {{value}}',
            'selectedItemColor': 'selectedItemColor: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'tabbar',
        'flutter_widget': 'TabBar',
        'properties_mapping': {
            'tabs': 'tabs: {{value}}',
            'controller': 'controller: {{value}}',
            'isScrollable': 'isScrollable: {{value}}',
            'indicatorColor': 'indicatorColor: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'snackbar',
        'flutter_widget': 'SnackBar',
        'properties_mapping': {
            'content': 'content: Text({{value}})',
            'backgroundColor': 'backgroundColor: {{value}}',
            'duration': 'duration: Duration(seconds: {{value}})',
            'action': 'action: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'alertdialog',
        'flutter_widget': 'AlertDialog',
        'properties_mapping': {
            'title': 'title: Text({{value}})',
            'content': 'content: Text({{value}})',
            'actions': 'actions: {{value}}',
            'backgroundColor': 'backgroundColor: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'bottomsheet',
        'flutter_widget': 'BottomSheet',
        'properties_mapping': {
            'onClosing': 'onClosing: {{value}}',
            'builder': 'builder: {{value}}',
            'backgroundColor': 'backgroundColor: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'expansiontile',
        'flutter_widget': 'ExpansionTile',
        'properties_mapping': {
            'title': 'title: Text({{value}})',
            'subtitle': 'subtitle: Text({{value}})',
            'leading': 'leading: {{value}}',
            'trailing': 'trailing: {{value}}',
            'children': 'children: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'stepper',
        'flutter_widget': 'Stepper',
        'properties_mapping': {
            'steps': 'steps: {{value}}',
            'currentStep': 'currentStep: {{value}}',
            'onStepContinue': 'onStepContinue: {{value}}',
            'onStepCancel': 'onStepCancel: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },

    # Styling Widgets
    {
        'ui_type': 'opacity',
        'flutter_widget': 'Opacity',
        'properties_mapping': {
            'opacity': 'opacity: {{value}}',
            'alwaysIncludeSemantics': 'alwaysIncludeSemantics: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'transform',
        'flutter_widget': 'Transform',
        'properties_mapping': {
            'transform': 'transform: {{value}}',
            'origin': 'origin: {{value}}',
            'alignment': 'alignment: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'decoratedbox',
        'flutter_widget': 'DecoratedBox',
        'properties_mapping': {
            'decoration': 'decoration: {{value}}',
            'position': 'position: DecorationPosition.{{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'cliprrect',
        'flutter_widget': 'ClipRRect',
        'properties_mapping': {
            'borderRadius': 'borderRadius: BorderRadius.circular({{value}}.0)',
            'clipBehavior': 'clipBehavior: Clip.{{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'hero',
        'flutter_widget': 'Hero',
        'properties_mapping': {
            'tag': 'tag: {{value}}',
            'createRectTween': 'createRectTween: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },

    # Additional useful widgets
    {
        'ui_type': 'gesturedetector',
        'flutter_widget': 'GestureDetector',
        'properties_mapping': {
            'onTap': 'onTap: {{value}}',
            'onDoubleTap': 'onDoubleTap: {{value}}',
            'onLongPress': 'onLongPress: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'inkwell',
        'flutter_widget': 'InkWell',
        'properties_mapping': {
            'onTap': 'onTap: {{value}}',
            'borderRadius': 'borderRadius: BorderRadius.circular({{value}}.0)',
            'splashColor': 'splashColor: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'badge',
        'flutter_widget': 'Badge',
        'properties_mapping': {
            'label': 'label: Text({{value}})',
            'backgroundColor': 'backgroundColor: {{value}}',
            'largeSize': 'largeSize: {{value}}.0',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'scrollable',
        'flutter_widget': 'SingleChildScrollView',
        'properties_mapping': {
            'scrollDirection': 'scrollDirection: Axis.{{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'grid',
        'flutter_widget': 'GridView.count',
        'properties_mapping': {
            'crossAxisCount': 'crossAxisCount: {{value}}',
            'mainAxisSpacing': 'mainAxisSpacing: {{value}}.0',
            'crossAxisSpacing': 'crossAxisSpacing: {{value}}.0',
            'padding': 'padding: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'spacer',
        'flutter_widget': 'Spacer',
        'properties_mapping': {
            'flex': 'flex: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    # Missing Layout Widgets
    {
        'ui_type': 'spacer',
        'flutter_widget': 'Spacer',
        'properties_mapping': {
            'flex': 'flex: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'scrollable',
        'flutter_widget': 'SingleChildScrollView',
        'properties_mapping': {
            'scrollDirection': 'scrollDirection: Axis.{{value}}',
            'reverse': 'reverse: {{value}}',
            'padding': 'padding: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'singlechildscrollview',
        'flutter_widget': 'SingleChildScrollView',
        'properties_mapping': {
            'scrollDirection': 'scrollDirection: Axis.{{value}}',
            'reverse': 'reverse: {{value}}',
            'padding': 'padding: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'grid',
        'flutter_widget': 'GridView.count',
        'properties_mapping': {
            'crossAxisCount': 'crossAxisCount: {{value}}',
            'mainAxisSpacing': 'mainAxisSpacing: {{value}}',
            'crossAxisSpacing': 'crossAxisSpacing: {{value}}',
            'childAspectRatio': 'childAspectRatio: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'positioned',
        'flutter_widget': 'Positioned',
        'properties_mapping': {
            'left': 'left: {{value}}',
            'top': 'top: {{value}}',
            'right': 'right: {{value}}',
            'bottom': 'bottom: {{value}}',
            'width': 'width: {{value}}',
            'height': 'height: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'align',
        'flutter_widget': 'Align',
        'properties_mapping': {
            'alignment': 'alignment: {{value}}',
            'widthFactor': 'widthFactor: {{value}}',
            'heightFactor': 'heightFactor: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'aspectratio',
        'flutter_widget': 'AspectRatio',
        'properties_mapping': {
            'aspectRatio': 'aspectRatio: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'constrainedbox',
        'flutter_widget': 'ConstrainedBox',
        'properties_mapping': {
            'minWidth': 'constraints: BoxConstraints(minWidth: {{value}})',
            'minHeight': 'constraints: BoxConstraints(minHeight: {{value}})',
            'maxWidth': 'constraints: BoxConstraints(maxWidth: {{value}})',
            'maxHeight': 'constraints: BoxConstraints(maxHeight: {{value}})',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'fittedbox',
        'flutter_widget': 'FittedBox',
        'properties_mapping': {
            'fit': 'fit: BoxFit.{{value}}',
            'alignment': 'alignment: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'fractionallysizedbox',
        'flutter_widget': 'FractionallySizedBox',
        'properties_mapping': {
            'widthFactor': 'widthFactor: {{value}}',
            'heightFactor': 'heightFactor: {{value}}',
            'alignment': 'alignment: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'intrinsicheight',
        'flutter_widget': 'IntrinsicHeight',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'intrinsicwidth',
        'flutter_widget': 'IntrinsicWidth',
        'properties_mapping': {
            'stepWidth': 'stepWidth: {{value}}',
            'stepHeight': 'stepHeight: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'limitedbox',
        'flutter_widget': 'LimitedBox',
        'properties_mapping': {
            'maxWidth': 'maxWidth: {{value}}',
            'maxHeight': 'maxHeight: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'offstage',
        'flutter_widget': 'Offstage',
        'properties_mapping': {
            'offstage': 'offstage: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'overflowbox',
        'flutter_widget': 'OverflowBox',
        'properties_mapping': {
            'minWidth': 'minWidth: {{value}}',
            'minHeight': 'minHeight: {{value}}',
            'maxWidth': 'maxWidth: {{value}}',
            'maxHeight': 'maxHeight: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'table',
        'flutter_widget': 'Table',
        'properties_mapping': {
            'border': 'border: TableBorder.all()',
            'columnWidths': 'columnWidths: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },

    # Missing Display Widgets
    {
        'ui_type': 'placeholder',
        'flutter_widget': 'Placeholder',
        'properties_mapping': {
            'color': 'color: {{value}}',
            'strokeWidth': 'strokeWidth: {{value}}',
            'fallbackWidth': 'fallbackWidth: {{value}}',
            'fallbackHeight': 'fallbackHeight: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'circleavatar',
        'flutter_widget': 'CircleAvatar',
        'properties_mapping': {
            'radius': 'radius: {{value}}',
            'backgroundColor': 'backgroundColor: {{value}}',
            'backgroundImage': 'backgroundImage: NetworkImage({{value}})',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'tooltip',
        'flutter_widget': 'Tooltip',
        'properties_mapping': {
            'message': 'message: {{value}}',
            'height': 'height: {{value}}',
            'padding': 'padding: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'badge',
        'flutter_widget': 'Badge',
        'properties_mapping': {
            'label': 'label: Text({{value}})',
            'backgroundColor': 'backgroundColor: {{value}}',
            'textColor': 'textColor: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'datatable',
        'flutter_widget': 'DataTable',
        'properties_mapping': {
            'columns': 'columns: {{value}}',
            'rows': 'rows: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },

    # Missing Input Widgets
    {
        'ui_type': 'form',
        'flutter_widget': 'Form',
        'properties_mapping': {
            'autovalidateMode': 'autovalidateMode: AutovalidateMode.{{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'radiolisttile',
        'flutter_widget': 'RadioListTile',
        'properties_mapping': {
            'title': 'title: Text({{value}})',
            'value': 'value: {{value}}',
            'groupValue': 'groupValue: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'checkboxlisttile',
        'flutter_widget': 'CheckboxListTile',
        'properties_mapping': {
            'title': 'title: Text({{value}})',
            'value': 'value: {{value}}',
            'subtitle': 'subtitle: Text({{value}})',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'switchlisttile',
        'flutter_widget': 'SwitchListTile',
        'properties_mapping': {
            'title': 'title: Text({{value}})',
            'value': 'value: {{value}}',
            'subtitle': 'subtitle: Text({{value}})',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'rangeslider',
        'flutter_widget': 'RangeSlider',
        'properties_mapping': {
            'values': 'values: RangeValues({{value}})',
            'min': 'min: {{value}}',
            'max': 'max: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'popupmenubutton',
        'flutter_widget': 'PopupMenuButton',
        'properties_mapping': {
            'icon': 'icon: Icon(Icons.{{value}})',
            'itemBuilder': 'itemBuilder: (context) => []',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },

    # Missing Navigation Widgets
    {
        'ui_type': 'navigationrail',
        'flutter_widget': 'NavigationRail',
        'properties_mapping': {
            'destinations': 'destinations: {{value}}',
            'selectedIndex': 'selectedIndex: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },

    # Missing Material Widgets
    {
        'ui_type': 'scaffold',
        'flutter_widget': 'Scaffold',
        'properties_mapping': {
            'backgroundColor': 'backgroundColor: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'sliverappbar',
        'flutter_widget': 'SliverAppBar',
        'properties_mapping': {
            'title': 'title: Text({{value}})',
            'floating': 'floating: {{value}}',
            'pinned': 'pinned: {{value}}',
            'expandedHeight': 'expandedHeight: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'fab',
        'flutter_widget': 'FloatingActionButton',
        'properties_mapping': {
            'onPressed': 'onPressed: {{value}}',
            'child': 'child: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'choicechip',
        'flutter_widget': 'ChoiceChip',
        'properties_mapping': {
            'label': 'label: Text({{value}})',
            'selected': 'selected: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'filterchip',
        'flutter_widget': 'FilterChip',
        'properties_mapping': {
            'label': 'label: Text({{value}})',
            'selected': 'selected: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'actionchip',
        'flutter_widget': 'ActionChip',
        'properties_mapping': {
            'label': 'label: Text({{value}})',
            'onPressed': 'onPressed: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'inputchip',
        'flutter_widget': 'InputChip',
        'properties_mapping': {
            'label': 'label: Text({{value}})',
            'onDeleted': 'onDeleted: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'banner',
        'flutter_widget': 'MaterialBanner',
        'properties_mapping': {
            'content': 'content: Text({{value}})',
            'actions': 'actions: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'navigationbar',
        'flutter_widget': 'NavigationBar',
        'properties_mapping': {
            'destinations': 'destinations: {{value}}',
            'selectedIndex': 'selectedIndex: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },
    {
        'ui_type': 'segmentedbutton',
        'flutter_widget': 'SegmentedButton',
        'properties_mapping': {
            'segments': 'segments: {{value}}',
            'selected': 'selected: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': False,
    },

    # Missing Animation/Transition Widgets
    {
        'ui_type': 'animatedcontainer',
        'flutter_widget': 'AnimatedContainer',
        'properties_mapping': {
            'duration': 'duration: Duration(milliseconds: {{value}})',
            'width': 'width: {{value}}',
            'height': 'height: {{value}}',
            'color': 'color: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'animatedopacity',
        'flutter_widget': 'AnimatedOpacity',
        'properties_mapping': {
            'opacity': 'opacity: {{value}}',
            'duration': 'duration: Duration(milliseconds: {{value}})',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'animatedpadding',
        'flutter_widget': 'AnimatedPadding',
        'properties_mapping': {
            'padding': 'padding: {{value}}',
            'duration': 'duration: Duration(milliseconds: {{value}})',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'animatedpositioned',
        'flutter_widget': 'AnimatedPositioned',
        'properties_mapping': {
            'duration': 'duration: Duration(milliseconds: {{value}})',
            'left': 'left: {{value}}',
            'top': 'top: {{value}}',
            'right': 'right: {{value}}',
            'bottom': 'bottom: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'animatedswitcher',
        'flutter_widget': 'AnimatedSwitcher',
        'properties_mapping': {
            'duration': 'duration: Duration(milliseconds: {{value}})',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },

    # Missing Utility Widgets
    {
        'ui_type': 'visibility',
        'flutter_widget': 'Visibility',
        'properties_mapping': {
            'visible': 'visible: {{value}}',
            'maintainState': 'maintainState: {{value}}',
            'maintainAnimation': 'maintainAnimation: {{value}}',
            'maintainSize': 'maintainSize: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'ignorepointer',
        'flutter_widget': 'IgnorePointer',
        'properties_mapping': {
            'ignoring': 'ignoring: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'absorbpointer',
        'flutter_widget': 'AbsorbPointer',
        'properties_mapping': {
            'absorbing': 'absorbing: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },

    # Missing Scrolling Widgets
    {
        'ui_type': 'customscrollview',
        'flutter_widget': 'CustomScrollView',
        'properties_mapping': {
            'scrollDirection': 'scrollDirection: Axis.{{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'nestedscrollview',
        'flutter_widget': 'NestedScrollView',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'refreshindicator',
        'flutter_widget': 'RefreshIndicator',
        'properties_mapping': {
            'onRefresh': 'onRefresh: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'scrollbar',
        'flutter_widget': 'Scrollbar',
        'properties_mapping': {
            'isAlwaysShown': 'isAlwaysShown: {{value}}',
            'thickness': 'thickness: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'draggablescrollablesheet',
        'flutter_widget': 'DraggableScrollableSheet',
        'properties_mapping': {
            'initialChildSize': 'initialChildSize: {{value}}',
            'minChildSize': 'minChildSize: {{value}}',
            'maxChildSize': 'maxChildSize: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },

    # Missing Other Common Widgets
    {
        'ui_type': 'gesturedetector',
        'flutter_widget': 'GestureDetector',
        'properties_mapping': {
            'onTap': 'onTap: {{value}}',
            'onDoubleTap': 'onDoubleTap: {{value}}',
            'onLongPress': 'onLongPress: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'inkwell',
        'flutter_widget': 'InkWell',
        'properties_mapping': {
            'onTap': 'onTap: {{value}}',
            'borderRadius': 'borderRadius: BorderRadius.circular({{value}})',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'material',
        'flutter_widget': 'Material',
        'properties_mapping': {
            'color': 'color: {{value}}',
            'elevation': 'elevation: {{value}}',
            'type': 'type: MaterialType.{{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'pageview',
        'flutter_widget': 'PageView',
        'properties_mapping': {
            'scrollDirection': 'scrollDirection: Axis.{{value}}',
            'pageSnapping': 'pageSnapping: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'indexedstack',
        'flutter_widget': 'IndexedStack',
        'properties_mapping': {
            'index': 'index: {{value}}',
            'alignment': 'alignment: {{value}}',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'flow',
        'flutter_widget': 'Flow',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'custompaint',
        'flutter_widget': 'CustomPaint',
        'properties_mapping': {
            'size': 'size: Size({{value}})',
        },
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'clipoval',
        'flutter_widget': 'ClipOval',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'clippath',
        'flutter_widget': 'ClipPath',
        'properties_mapping': {},
        'import_statements': "import 'package:flutter/material.dart';",
        'can_have_children': True,
    },
    {
        'ui_type': 'backdropfilter',
        'flutter_widget': 'BackdropFilter',
        'properties_mapping': {
            'filter': 'filter: ImageFilter.blur(sigmaX: {{value}}, sigmaY: {{value}})',
        },
        'import_statements': "import 'package:flutter/material.dart';\nimport 'dart:ui';",
        'can_have_children': True,
    },
]

print("Adding all widget mappings...\n")

# Clear existing mappings first (optional)
# WidgetMapping.objects.all().delete()

# Add all mappings
created_count = 0
updated_count = 0

for mapping_data in all_widget_mappings:
    widget_mapping, created = WidgetMapping.objects.update_or_create(
        ui_type=mapping_data['ui_type'],
        defaults=mapping_data
    )
    if created:
        print(f"✓ Created mapping for {mapping_data['ui_type']}")
        created_count += 1
    else:
        print(f"✓ Updated mapping for {mapping_data['ui_type']}")
        updated_count += 1

print(f"\n{'='*50}")
print(f"Total widget mappings: {len(all_widget_mappings)}")
print(f"Created: {created_count}")
print(f"Updated: {updated_count}")
print(f"{'='*50}")

# Verify all mappings
print("\nVerifying widget mappings...")
db_count = WidgetMapping.objects.filter(is_active=True).count()
print(f"Active widget mappings in database: {db_count}")

# List all UI types
print("\nAvailable widget types:")
for mapping in WidgetMapping.objects.filter(is_active=True).order_by('ui_type'):
    print(f"  - {mapping.ui_type} → {mapping.flutter_widget}")

print("\n✅ All widget mappings have been added successfully!")