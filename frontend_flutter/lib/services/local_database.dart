import 'dart:convert';

import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

class LocalDatabaseService {
  static final LocalDatabaseService _instance = LocalDatabaseService._();

  factory LocalDatabaseService() => _instance;

  LocalDatabaseService._();

  static const _dbName = 'nova_local_admin.db';
  static const _dbVersion = 3;

  Database? _db;

  Future<Database> _database() async {
    if (_db != null) return _db!;
    final basePath = await getDatabasesPath();
    final path = p.join(basePath, _dbName);

    _db = await openDatabase(
      path,
      version: _dbVersion,
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE knowledge (
            id TEXT PRIMARY KEY,
            gatilho TEXT NOT NULL,
            resposta TEXT NOT NULL,
            categoria TEXT NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1,
            criado_em TEXT,
            atualizado_em TEXT
          )
        ''');

        await db.execute('''
          CREATE TABLE users (
            id TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            papel TEXT NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1,
            desde INTEGER,
            criado_em TEXT
          )
        ''');

        await db.execute('''
          CREATE TABLE config (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
          )
        ''');

        await db.execute('''
          CREATE TABLE music_library (
            path TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            added_at TEXT
          )
        ''');

        await db.execute('''
          CREATE TABLE reminders (
            id TEXT PRIMARY KEY,
            texto TEXT NOT NULL,
            quando TEXT,
            criado_em TEXT,
            feito INTEGER NOT NULL DEFAULT 0
          )
        ''');
      },
      onUpgrade: (db, oldVersion, newVersion) async {
        if (oldVersion < 2) {
          await db.execute('''
            CREATE TABLE IF NOT EXISTS music_library (
              path TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              added_at TEXT
            )
          ''');
        }
        if (oldVersion < 3) {
          await db.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
              id TEXT PRIMARY KEY,
              texto TEXT NOT NULL,
              quando TEXT,
              criado_em TEXT,
              feito INTEGER NOT NULL DEFAULT 0
            )
          ''');
        }
      },
    );

    return _db!;
  }

  Future<void> close() async {
    if (_db != null) {
      await _db!.close();
      _db = null;
    }
  }

  Future<void> saveAdminState({
    required List<Map<String, dynamic>> knowledge,
    required List<Map<String, dynamic>> users,
    required Map<String, dynamic> config,
  }) async {
    final db = await _database();

    await db.transaction((txn) async {
      await txn.delete('knowledge');
      await txn.delete('users');
      await txn.delete('config');

      for (final item in knowledge) {
        final row = <String, dynamic>{
          'id': (item['id'] ?? '').toString(),
          'gatilho': (item['gatilho'] ?? '').toString(),
          'resposta': (item['resposta'] ?? '').toString(),
          'categoria': (item['categoria'] ?? 'geral').toString(),
          'ativo': _toSqlBool(item['ativo']),
          'criado_em': item['criado_em']?.toString(),
          'atualizado_em': item['atualizado_em']?.toString(),
        };
        if ((row['id'] as String).isEmpty ||
            (row['gatilho'] as String).isEmpty ||
            (row['resposta'] as String).isEmpty) {
          continue;
        }
        await txn.insert('knowledge', row);
      }

      for (final user in users) {
        final row = <String, dynamic>{
          'id': (user['id'] ?? '').toString(),
          'nome': (user['nome'] ?? '').toString(),
          'papel': (user['papel'] ?? 'usuario').toString(),
          'ativo': _toSqlBool(user['ativo']),
          'desde': _toInt(user['desde']),
          'criado_em': user['criado_em']?.toString(),
        };
        if ((row['id'] as String).isEmpty || (row['nome'] as String).isEmpty) {
          continue;
        }
        await txn.insert('users', row);
      }

      for (final entry in config.entries) {
        await txn.insert(
          'config',
          {
            'chave': entry.key,
            'valor': jsonEncode(entry.value),
          },
        );
      }
    });
  }

  Future<Map<String, dynamic>> loadAdminState() async {
    final db = await _database();

    final knowledgeRows =
        await db.query('knowledge', orderBy: 'categoria, gatilho');
    final usersRows =
        await db.query('users', orderBy: 'nome COLLATE NOCASE ASC');
    final configRows = await db.query('config');

    final knowledge = knowledgeRows
        .map(
          (row) => {
            'id': row['id'],
            'gatilho': row['gatilho'],
            'resposta': row['resposta'],
            'categoria': row['categoria'],
            'ativo': _fromSqlBool(row['ativo']),
            'criado_em': row['criado_em'],
            'atualizado_em': row['atualizado_em'],
          },
        )
        .toList();

    final users = usersRows
        .map(
          (row) => {
            'id': row['id'],
            'nome': row['nome'],
            'papel': row['papel'],
            'ativo': _fromSqlBool(row['ativo']),
            'desde': row['desde'],
            'criado_em': row['criado_em'],
          },
        )
        .toList();

    final config = <String, dynamic>{};
    for (final row in configRows) {
      final key = row['chave']?.toString() ?? '';
      if (key.isEmpty) continue;
      final raw = row['valor']?.toString() ?? 'null';
      try {
        config[key] = jsonDecode(raw);
      } catch (_) {
        config[key] = raw;
      }
    }

    return {
      'knowledge': knowledge,
      'users': users,
      'config': config,
    };
  }

  Future<void> addMusicFiles(List<Map<String, String>> files) async {
    final db = await _database();
    final now = DateTime.now().toIso8601String();
    await db.transaction((txn) async {
      for (final item in files) {
        final path = (item['path'] ?? '').trim();
        final name = (item['name'] ?? '').trim();
        if (path.isEmpty || name.isEmpty) continue;
        await txn.insert(
          'music_library',
          {'path': path, 'name': name, 'added_at': now},
          conflictAlgorithm: ConflictAlgorithm.replace,
        );
      }
    });
  }

  Future<List<Map<String, String>>> getMusicLibrary() async {
    final db = await _database();
    final rows =
        await db.query('music_library', orderBy: 'name COLLATE NOCASE ASC');
    return rows
        .map((r) => {
              'path': (r['path'] ?? '').toString(),
              'name': (r['name'] ?? '').toString()
            })
        .where((e) => e['path']!.isNotEmpty && e['name']!.isNotEmpty)
        .toList();
  }

  Future<void> clearMusicLibrary() async {
    final db = await _database();
    await db.delete('music_library');
  }

  Future<void> upsertReminder(Map<String, dynamic> reminder) async {
    final db = await _database();
    final id = (reminder['id'] ?? '').toString().trim();
    final texto = (reminder['texto'] ?? '').toString().trim();
    if (id.isEmpty || texto.isEmpty) return;
    await db.insert(
      'reminders',
      {
        'id': id,
        'texto': texto,
        'quando': (reminder['quando'] ?? '').toString(),
        'criado_em': (reminder['criado_em'] ?? '').toString(),
        'feito': _toSqlBool(reminder['feito']),
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<void> saveReminders(List<Map<String, dynamic>> reminders) async {
    final db = await _database();
    await db.transaction((txn) async {
      await txn.delete('reminders');
      for (final item in reminders) {
        final id = (item['id'] ?? '').toString().trim();
        final texto = (item['texto'] ?? '').toString().trim();
        if (id.isEmpty || texto.isEmpty) continue;
        await txn.insert('reminders', {
          'id': id,
          'texto': texto,
          'quando': (item['quando'] ?? '').toString(),
          'criado_em': (item['criado_em'] ?? '').toString(),
          'feito': _toSqlBool(item['feito']),
        });
      }
    });
  }

  Future<List<Map<String, dynamic>>> getReminders() async {
    final db = await _database();
    final rows = await db.query(
      'reminders',
      orderBy: 'coalesce(quando, criado_em) DESC',
    );
    return rows
        .map((r) => {
              'id': (r['id'] ?? '').toString(),
              'texto': (r['texto'] ?? '').toString(),
              'quando': (r['quando'] ?? '').toString(),
              'criado_em': (r['criado_em'] ?? '').toString(),
              'feito': _fromSqlBool(r['feito']),
            })
        .where((e) =>
            (e['id']?.toString().isNotEmpty ?? false) &&
            (e['texto']?.toString().isNotEmpty ?? false))
        .toList();
  }

  int _toSqlBool(dynamic value) {
    if (value is bool) return value ? 1 : 0;
    if (value is num) return value != 0 ? 1 : 0;
    final text = value?.toString().toLowerCase();
    if (text == 'true' || text == '1' || text == 'sim') return 1;
    return 0;
  }

  bool _fromSqlBool(dynamic value) {
    if (value is bool) return value;
    if (value is num) return value != 0;
    final text = value?.toString().toLowerCase();
    return text == 'true' || text == '1' || text == 'sim';
  }

  int? _toInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse(value?.toString() ?? '');
  }
}
