import 'package:flutter/material.dart';

import 'screens/splash_screen.dart';
import 'theme/soundscape_theme.dart';

class CrjSoundScapeApp extends StatelessWidget {
  const CrjSoundScapeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'CRJ SoundScape',
      debugShowCheckedModeBanner: false,
      theme: SoundScapeTheme.darkTheme,
      home: const SplashScreen(),
    );
  }
}
