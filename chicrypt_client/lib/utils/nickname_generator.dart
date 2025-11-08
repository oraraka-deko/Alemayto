import 'dart:math';

class NicknameGenerator {
  static final List<String> adjectives = [
    'Happy', 'Swift', 'Brave', 'Calm', 'Bright', 'Cool', 'Smart', 'Kind',
    'Lucky', 'Quick', 'Wise', 'Bold', 'Keen', 'Neat', 'Pure', 'True',
    'Wild', 'Zany', 'Eager', 'Fancy', 'Jolly', 'Merry', 'Noble', 'Proud',
  ];

  static final List<String> nouns = [
    'Panda', 'Tiger', 'Eagle', 'Dolphin', 'Phoenix', 'Dragon', 'Wolf', 'Fox',
    'Falcon', 'Lion', 'Bear', 'Hawk', 'Owl', 'Shark', 'Lynx', 'Raven',
    'Falcon', 'Panther', 'Jaguar', 'Cheetah', 'Leopard', 'Cobra', 'Viper',
  ];

  static String generate() {
    final random = Random();
    final adjective = adjectives[random.nextInt(adjectives.length)];
    final noun = nouns[random.nextInt(nouns.length)];
    final number = random.nextInt(1000);
    
    return '$adjective$noun$number';
  }
}
