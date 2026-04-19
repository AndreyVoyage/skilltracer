const tg = (window as any).Telegram?.WebApp;

// eslint-disable-next-line no-console
console.group('🔍 [Telegram WebApp Debug]');
// eslint-disable-next-line no-console
console.log('WebApp exists:', !!tg);
// eslint-disable-next-line no-console
console.log('initData present:', !!tg?.initData);
// eslint-disable-next-line no-console
console.log('initData length:', tg?.initData?.length || 0);
// eslint-disable-next-line no-console
console.log('initDataUnsafe.user:', tg?.initDataUnsafe?.user);
// eslint-disable-next-line no-console
console.log('platform:', tg?.platform);
// eslint-disable-next-line no-console
console.log('version:', tg?.version);
// eslint-disable-next-line no-console
console.log('colorScheme:', tg?.colorScheme);
// eslint-disable-next-line no-console
console.groupEnd();

// Предупреждение если открыто не в Telegram
if (!tg) {
  // eslint-disable-next-line no-console
  console.warn('⚠️ Not running inside Telegram WebView!');
  // eslint-disable-next-line no-console
  console.warn('Open via Telegram Bot button for full functionality');
}
