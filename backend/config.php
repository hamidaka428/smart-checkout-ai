<?php
// Database configuration.
// Values come from environment variables or, if present, from config.local.php
// (copy config.local.php.example; that file is git-ignored so passwords never get committed).

$local = __DIR__ . '/config.local.php';
$cfg = file_exists($local) ? require $local : [];

return [
    'host' => $cfg['host'] ?? getenv('DB_HOST') ?: 'localhost',
    'name' => $cfg['name'] ?? getenv('DB_NAME') ?: 'smart_checkout',
    'user' => $cfg['user'] ?? getenv('DB_USER') ?: 'smart_checkout',
    'pass' => $cfg['pass'] ?? getenv('DB_PASS') ?: '',
];
