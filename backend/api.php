<?php
// GET /api.php?barcode=RPI_MOUSE
// -> {"barcode":"RPI_MOUSE","name":"Wireless Computer Mouse","price":9.2}
// On failure the response contains an "error" field (the Python client checks for it).

require __DIR__ . '/db.php';

if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    json_response(['error' => 'Method not allowed'], 405);
}

$barcode = $_GET['barcode'] ?? '';
if (!is_string($barcode) || !preg_match('/^[A-Za-z0-9_\-]{1,50}$/', $barcode)) {
    json_response(['error' => 'Missing or invalid barcode'], 400);
}

try {
    $stmt = db()->prepare('SELECT barcode, name, price FROM products WHERE barcode = ?');
    $stmt->execute([$barcode]);
    $product = $stmt->fetch();
} catch (Throwable $e) {
    error_log('api.php: ' . $e->getMessage());
    json_response(['error' => 'Database error'], 500);
}

if (!$product) {
    json_response(['error' => 'Product not found'], 404);
}

$product['price'] = (float) $product['price'];
json_response($product);
