<?php
// POST /save_order.php   (Content-Type: application/json)
// Body:     {"total_amount": 169.5, "vat_amount": 28.25, "items_count": 11}
// Response: {"success": true, "order_id": 39}

require __DIR__ . '/db.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    json_response(['error' => 'Method not allowed'], 405);
}

$raw = file_get_contents('php://input', false, null, 0, 4096);
$data = json_decode($raw ?: '', true);
if (!is_array($data)) {
    json_response(['error' => 'Invalid JSON body'], 400);
}

$total = $data['total_amount'] ?? null;
$vat   = $data['vat_amount'] ?? null;
$items = $data['items_count'] ?? null;

$valid = is_numeric($total) && is_numeric($vat) && is_numeric($items)
      && $total >= 0 && $vat >= 0 && $vat <= $total
      && (int) $items == $items && $items >= 1 && $items <= 1000
      && $total < 100000000;
if (!$valid) {
    json_response(['error' => 'Invalid order values'], 422);
}

try {
    $stmt = db()->prepare(
        'INSERT INTO orders (total_amount, vat_amount, items_count) VALUES (?, ?, ?)'
    );
    $stmt->execute([round((float) $total, 2), round((float) $vat, 2), (int) $items]);
    json_response(['success' => true, 'order_id' => (int) db()->lastInsertId()], 201);
} catch (Throwable $e) {
    error_log('save_order.php: ' . $e->getMessage());
    json_response(['error' => 'Database error'], 500);
}
