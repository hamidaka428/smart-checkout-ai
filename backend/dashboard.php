<?php
// Live sales dashboard: http://localhost/dashboard.php
require __DIR__ . '/db.php';

function e($v): string { return htmlspecialchars((string) $v, ENT_QUOTES, 'UTF-8'); }
function eur($v): string { return '€' . number_format((float) $v, 2); }

try {
    $pdo = db();
    $totals = $pdo->query(
        'SELECT COUNT(*) AS orders, COALESCE(SUM(total_amount),0) AS revenue,
                COALESCE(SUM(vat_amount),0) AS vat, COALESCE(SUM(items_count),0) AS items,
                COALESCE(AVG(total_amount),0) AS avg_order
         FROM orders'
    )->fetch();
    $daily = $pdo->query(
        'SELECT DATE(created_at) AS day, COUNT(*) AS orders, SUM(total_amount) AS revenue
         FROM orders GROUP BY DATE(created_at) ORDER BY day DESC LIMIT 14'
    )->fetchAll();
    $recent = $pdo->query(
        'SELECT id, created_at, items_count, total_amount, vat_amount
         FROM orders ORDER BY id DESC LIMIT 20'
    )->fetchAll();
} catch (Throwable $ex) {
    error_log('dashboard.php: ' . $ex->getMessage());
    http_response_code(500);
    exit('Database error');
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="10">
<title>Smart Checkout – Dashboard</title>
<style>
  :root { --bg:#0d1117; --card:#161b22; --line:#30363d; --text:#e6edf3; --muted:#8b949e; --acc:#38bdf8; }
  * { box-sizing: border-box; }
  body { margin:0; padding:32px; background:var(--bg); color:var(--text);
         font:16px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
  h1 { margin:0 0 4px; font-size:28px; } .sub { color:var(--muted); margin-bottom:28px; }
  .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:16px; margin-bottom:32px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:18px; }
  .card .label { color:var(--muted); font-size:13px; text-transform:uppercase; letter-spacing:.05em; }
  .card .value { font-size:28px; font-weight:700; color:var(--acc); margin-top:4px; }
  h2 { font-size:18px; margin:28px 0 10px; }
  table { width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--line); border-radius:10px; overflow:hidden; }
  th, td { padding:10px 14px; text-align:left; border-bottom:1px solid var(--line); }
  th { color:var(--muted); font-size:13px; text-transform:uppercase; letter-spacing:.05em; }
  td.num, th.num { text-align:right; font-variant-numeric:tabular-nums; }
  tr:last-child td { border-bottom:none; }
  .empty { color:var(--muted); padding:18px; }
</style>
</head>
<body>
  <h1>Smart Checkout</h1>
  <div class="sub">Sales analytics · refreshes every 10 s</div>

  <div class="cards">
    <div class="card"><div class="label">Orders</div><div class="value"><?= e($totals['orders']) ?></div></div>
    <div class="card"><div class="label">Revenue</div><div class="value"><?= e(eur($totals['revenue'])) ?></div></div>
    <div class="card"><div class="label">VAT collected</div><div class="value"><?= e(eur($totals['vat'])) ?></div></div>
    <div class="card"><div class="label">Items sold</div><div class="value"><?= e($totals['items']) ?></div></div>
    <div class="card"><div class="label">Avg. order</div><div class="value"><?= e(eur($totals['avg_order'])) ?></div></div>
  </div>

  <h2>Last 14 days</h2>
  <?php if (!$daily): ?><div class="empty">No orders yet.</div><?php else: ?>
  <table>
    <tr><th>Date</th><th class="num">Orders</th><th class="num">Revenue</th></tr>
    <?php foreach ($daily as $d): ?>
      <tr><td><?= e($d['day']) ?></td><td class="num"><?= e($d['orders']) ?></td><td class="num"><?= e(eur($d['revenue'])) ?></td></tr>
    <?php endforeach; ?>
  </table>
  <?php endif; ?>

  <h2>Recent orders</h2>
  <?php if (!$recent): ?><div class="empty">No orders yet.</div><?php else: ?>
  <table>
    <tr><th>Order</th><th>Time</th><th class="num">Items</th><th class="num">VAT</th><th class="num">Total</th></tr>
    <?php foreach ($recent as $o): ?>
      <tr>
        <td>#<?= e($o['id']) ?></td><td><?= e($o['created_at']) ?></td>
        <td class="num"><?= e($o['items_count']) ?></td>
        <td class="num"><?= e(eur($o['vat_amount'])) ?></td>
        <td class="num"><?= e(eur($o['total_amount'])) ?></td>
      </tr>
    <?php endforeach; ?>
  </table>
  <?php endif; ?>
</body>
</html>
