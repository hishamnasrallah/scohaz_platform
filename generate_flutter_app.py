import os

project_name = "my_flutter_app"

# 1. أنشئ مجلد المشروع
os.system(f"flutter create {project_name}")

# 2. أنشئ كود الصفحة الحمراء
main_dart_code = '''
import 'package:flutter/material.dart';

void main() => runApp(MyApp());

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: Scaffold(
        backgroundColor: Colors.red,
        body: Center(),
      ),
    );
  }
}
'''

# 3. استبدل ملف main.dart
main_dart_path = os.path.join(project_name, "lib", "main.dart")
with open(main_dart_path, "w") as f:
    f.write(main_dart_code)

print("✅ Flutter project created with a red screen!")
print(f"📁 Project folder: {project_name}")
print("🚀 To build APK: cd into folder then run: flutter build apk")
