import 'package:flutter/material.dart';

import '../theme/soundscape_theme.dart';
import 'analysis_screen.dart';
import 'composer_screen.dart';
import 'about_screen.dart';
import 'manual_screen.dart';
import 'player_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _currentIndex = 0;

  final _screens = const [
    PlayerScreen(),
    ComposerScreen(),
    AnalysisScreen(),
    ManualScreen(),
    AboutScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(index: _currentIndex, children: _screens),
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          border: Border(
            top: BorderSide(color: SoundScapeTheme.cardBorder, width: 1),
          ),
        ),
        child: BottomNavigationBar(
          currentIndex: _currentIndex,
          onTap: (i) => setState(() => _currentIndex = i),
          items: const [
            BottomNavigationBarItem(
              icon: Icon(Icons.music_note_rounded),
              label: 'PLAYER',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.edit_note_rounded),
              label: 'COMPOSE',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.graphic_eq_rounded),
              label: 'ANALYZE',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.menu_book_rounded),
              label: 'MANUAL',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.info_outline_rounded),
              label: 'ABOUT',
            ),
          ],
        ),
      ),
    );
  }
}
