"""Constants for Flutter code generation"""

# Flutter SDK versions
FLUTTER_VERSIONS = {
    '3.0.0': {'dart': '2.17.0', 'min_sdk': 19},
    '3.3.0': {'dart': '2.18.0', 'min_sdk': 19},
    '3.7.0': {'dart': '2.19.0', 'min_sdk': 19},
    '3.10.0': {'dart': '3.0.0', 'min_sdk': 19},
    '3.13.0': {'dart': '3.1.0', 'min_sdk': 19},
    '3.16.0': {'dart': '3.2.0', 'min_sdk': 21},
}

DEFAULT_FLUTTER_VERSION = '3.16.0'

# Widget categories
WIDGET_CATEGORIES = {
    'layout': [
        'container', 'row', 'column', 'stack', 'wrap', 'flow',
        'expanded', 'flexible', 'positioned', 'align', 'center',
        'padding', 'sizedbox', 'aspectratio', 'constrainedbox',
        'fittedbox', 'fractionallysizedbox', 'intrinsicheight',
        'intrinsicwidth', 'limitedbox', 'offstage', 'overflow',
        'overflowbox', 'sizedoverflowbox'
    ],
    'input': [
        'textfield', 'textformfield', 'checkbox', 'radio', 'switch',
        'slider', 'rangeslider', 'datepicker', 'timepicker',
        'dropdown', 'autocomplete', 'chip', 'inputchip', 'choicechip',
        'filterchip', 'actionchip'
    ],
    'display': [
        'text', 'richtext', 'image', 'icon', 'circleavatar',
        'chip', 'tooltip', 'progressindicator', 'linearprogressindicator',
        'circularprogressindicator', 'refreshindicator'
    ],
    'button': [
        'elevatedbutton', 'textbutton', 'outlinedbutton', 'iconbutton',
        'floatingactionbutton', 'popupmenubutton', 'dropdownbutton'
    ],
    'navigation': [
        'appbar', 'bottomnavigationbar', 'navigationrail', 'drawer',
        'bottomsheet', 'tabbar', 'tabbarview', 'pageview',
        'navigationdrawer', 'breadcrumb'
    ],
    'material': [
        'scaffold', 'card', 'listtile', 'gridtile', 'expansiontile',
        'stepper', 'snackbar', 'banner', 'bottomappbar', 'navigationbar'
    ],
    'scrolling': [
        'listview', 'gridview', 'customscrollview', 'singlechildscrollview',
        'scrollbar', 'draggablescrollablesheet', 'nestedscrollview',
        'refreshindicator', 'reorderablelistview'
    ],
    'animation': [
        'animatedcontainer', 'animatedopacity', 'animatedpadding',
        'animatedpositioned', 'animatedsize', 'animatedwidget',
        'animatedbuilder', 'hero', 'animatedicon', 'animatedlist',
        'animatedgrid', 'fadetransition', 'scaletransition',
        'slidetransition', 'rotationtransition'
    ],
    'interaction': [
        'gesturedetector', 'inkwell', 'dismissible', 'draggable',
        'longpressdraggable', 'dragtarget', 'interactiveviewer',
        'absorbpointer', 'ignorepointer'
    ],
    'styling': [
        'theme', 'decoratedbox', 'opacity', 'cliprect', 'cliprrect',
        'clipoval', 'clippath', 'custompaint', 'backdrop', 'shader'
    ],
    'async': [
        'futurebuilder', 'streambuilder', 'valuelistenablebuilder',
        'animatedbuilder', 'builder'
    ],
    'other': [
        'placeholder', 'divider', 'verticaldivider', 'spacer',
        'visibility', 'banner', 'closebutton', 'backbutton',
        'rawimage', 'customsinglechildlayout', 'custommultichildlayout'
    ]
}

# Default widget properties
DEFAULT_WIDGET_PROPERTIES = {
    'container': {
        'width': None,
        'height': None,
        'padding': None,
        'margin': None,
        'color': None,
        'decoration': None,
        'alignment': None,
        'constraints': None,
    },
    'text': {
        'content': '',
        'style': None,
        'textAlign': 'start',
        'overflow': 'ellipsis',
        'maxLines': None,
        'softWrap': True,
    },
    'button': {
        'text': 'Button',
        'onPressed': None,
        'style': None,
        'icon': None,
    },
    'textfield': {
        'controller': None,
        'hintText': '',
        'labelText': '',
        'obscureText': False,
        'keyboardType': 'text',
        'maxLines': 1,
        'decoration': None,
    },
    'image': {
        'source': '',
        'width': None,
        'height': None,
        'fit': 'contain',
        'alignment': 'center',
        'color': None,
        'colorBlendMode': None,
    },
    'icon': {
        'icon': 'help',
        'size': 24,
        'color': None,
    },
    'scaffold': {
        'appBar': None,
        'body': None,
        'drawer': None,
        'endDrawer': None,
        'bottomNavigationBar': None,
        'floatingActionButton': None,
        'floatingActionButtonLocation': None,
        'backgroundColor': None,
    },
    'appbar': {
        'title': '',
        'leading': None,
        'actions': [],
        'backgroundColor': None,
        'elevation': 4,
        'centerTitle': False,
        'toolbarHeight': None,
    },
    'column': {
        'mainAxisAlignment': 'start',
        'crossAxisAlignment': 'center',
        'mainAxisSize': 'max',
        'verticalDirection': 'down',
        'children': [],
    },
    'row': {
        'mainAxisAlignment': 'start',
        'crossAxisAlignment': 'center',
        'mainAxisSize': 'max',
        'textDirection': None,
        'children': [],
    },
    'listview': {
        'scrollDirection': 'vertical',
        'reverse': False,
        'shrinkWrap': False,
        'padding': None,
        'itemExtent': None,
        'children': [],
    },
    'card': {
        'elevation': 1,
        'shape': None,
        'color': None,
        'margin': None,
        'child': None,
    },
}

# Material Design colors
MATERIAL_COLORS = {
    'red': '#F44336',
    'pink': '#E91E63',
    'purple': '#9C27B0',
    'deepPurple': '#673AB7',
    'indigo': '#3F51B5',
    'blue': '#2196F3',
    'lightBlue': '#03A9F4',
    'cyan': '#00BCD4',
    'teal': '#009688',
    'green': '#4CAF50',
    'lightGreen': '#8BC34A',
    'lime': '#CDDC39',
    'yellow': '#FFEB3B',
    'amber': '#FFC107',
    'orange': '#FF9800',
    'deepOrange': '#FF5722',
    'brown': '#795548',
    'grey': '#9E9E9E',
    'blueGrey': '#607D8B',
    'black': '#000000',
    'white': '#FFFFFF',
}

# Text style presets
TEXT_STYLE_PRESETS = {
    'headline1': {
        'fontSize': 96,
        'fontWeight': 'w300',
        'letterSpacing': -1.5,
    },
    'headline2': {
        'fontSize': 60,
        'fontWeight': 'w300',
        'letterSpacing': -0.5,
    },
    'headline3': {
        'fontSize': 48,
        'fontWeight': 'normal',
        'letterSpacing': 0,
    },
    'headline4': {
        'fontSize': 34,
        'fontWeight': 'normal',
        'letterSpacing': 0.25,
    },
    'headline5': {
        'fontSize': 24,
        'fontWeight': 'normal',
        'letterSpacing': 0,
    },
    'headline6': {
        'fontSize': 20,
        'fontWeight': 'w500',
        'letterSpacing': 0.15,
    },
    'subtitle1': {
        'fontSize': 16,
        'fontWeight': 'normal',
        'letterSpacing': 0.15,
    },
    'subtitle2': {
        'fontSize': 14,
        'fontWeight': 'w500',
        'letterSpacing': 0.1,
    },
    'body1': {
        'fontSize': 16,
        'fontWeight': 'normal',
        'letterSpacing': 0.5,
    },
    'body2': {
        'fontSize': 14,
        'fontWeight': 'normal',
        'letterSpacing': 0.25,
    },
    'button': {
        'fontSize': 14,
        'fontWeight': 'w500',
        'letterSpacing': 1.25,
    },
    'caption': {
        'fontSize': 12,
        'fontWeight': 'normal',
        'letterSpacing': 0.4,
    },
    'overline': {
        'fontSize': 10,
        'fontWeight': 'normal',
        'letterSpacing': 1.5,
    },
}

# Icons mapping
COMMON_ICONS = {
    # Navigation
    'menu': 'Icons.menu',
    'back': 'Icons.arrow_back',
    'forward': 'Icons.arrow_forward',
    'up': 'Icons.arrow_upward',
    'down': 'Icons.arrow_downward',
    'close': 'Icons.close',

    # Actions
    'add': 'Icons.add',
    'remove': 'Icons.remove',
    'edit': 'Icons.edit',
    'delete': 'Icons.delete',
    'save': 'Icons.save',
    'share': 'Icons.share',
    'search': 'Icons.search',
    'filter': 'Icons.filter_list',
    'sort': 'Icons.sort',
    'refresh': 'Icons.refresh',
    'more': 'Icons.more_vert',

    # Status
    'check': 'Icons.check',
    'error': 'Icons.error',
    'warning': 'Icons.warning',
    'info': 'Icons.info',
    'help': 'Icons.help',

    # User
    'person': 'Icons.person',
    'people': 'Icons.people',
    'account': 'Icons.account_circle',
    'settings': 'Icons.settings',
    'logout': 'Icons.logout',
    'login': 'Icons.login',

    # Communication
    'email': 'Icons.email',
    'phone': 'Icons.phone',
    'message': 'Icons.message',
    'chat': 'Icons.chat',
    'notification': 'Icons.notifications',

    # Media
    'image': 'Icons.image',
    'camera': 'Icons.camera_alt',
    'video': 'Icons.videocam',
    'audio': 'Icons.audiotrack',
    'play': 'Icons.play_arrow',
    'pause': 'Icons.pause',
    'stop': 'Icons.stop',

    # Common
    'home': 'Icons.home',
    'favorite': 'Icons.favorite',
    'star': 'Icons.star',
    'location': 'Icons.location_on',
    'calendar': 'Icons.calendar_today',
    'time': 'Icons.access_time',
    'attach': 'Icons.attach_file',
    'download': 'Icons.download',
    'upload': 'Icons.upload',
}

# Build configurations
BUILD_MODES = {
    'debug': {
        'name': 'Debug',
        'description': 'Build with debugging enabled',
        'flags': ['--debug'],
    },
    'profile': {
        'name': 'Profile',
        'description': 'Build with profiling enabled',
        'flags': ['--profile'],
    },
    'release': {
        'name': 'Release',
        'description': 'Build for production release',
        'flags': ['--release'],
    },
}

# Target platforms
TARGET_PLATFORMS = {
    'android-arm': 'ARMv7 (32-bit)',
    'android-arm64': 'ARM64 (64-bit)',
    'android-x64': 'x86_64 (64-bit)',
    'android-x86': 'x86 (32-bit)',
}

# File templates
FILE_TEMPLATES = {
    '.gitignore': '''
# Miscellaneous
*.class
*.log
*.pyc
*.swp
.DS_Store
.atom/
.buildlog/
.history
.svn/
migrate_working_dir/

# IntelliJ related
*.iml
*.ipr
*.iws
.idea/

# The .vscode folder contains launch configuration and tasks you configure in
# VS Code which you may wish to be included in version control, so this line
# is commented out by default.
#.vscode/

# Flutter/Dart/Pub related
**/doc/api/
**/ios/Flutter/.last_build_id
.dart_tool/
.flutter-plugins
.flutter-plugins-dependencies
.packages
.pub-cache/
.pub/
/build/

# Symbolication related
app.*.symbols

# Obfuscation related
app.*.map.json

# Android Studio will place build artifacts here
/android/app/debug
/android/app/profile
/android/app/release
''',

    'analysis_options.yaml': '''
include: package:flutter_lints/flutter.yaml

linter:
  rules:
    - prefer_const_constructors
    - prefer_const_declarations
    - prefer_const_literals_to_create_immutables
    - prefer_final_fields
    - use_key_in_widget_constructors
    - avoid_print
    - prefer_single_quotes
    - sort_child_properties_last
''',
}

# Error messages
ERROR_MESSAGES = {
    'invalid_widget_type': 'Invalid widget type: {type}',
    'missing_required_property': 'Missing required property: {property}',
    'invalid_property_type': 'Invalid type for property {property}: expected {expected}, got {actual}',
    'circular_dependency': 'Circular dependency detected in widget tree',
    'flutter_not_found': 'Flutter SDK not found. Please install Flutter.',
    'build_failed': 'Build failed: {error}',
    'invalid_package_name': 'Invalid package name: {name}',
    'file_write_error': 'Failed to write file: {file}',
    'project_generation_failed': 'Failed to generate project: {error}',
}