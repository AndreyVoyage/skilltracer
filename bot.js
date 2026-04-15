const { Telegraf } = require('telegraf');

// ЗАМЕНИ НА СВОЙ ТОКЕН (новый, после ревокации!)
const BOT_TOKEN = '8685300793:AAGZ5djb-O7z9GZ_wn6kNCaz45brWMZyEEY'; 

const bot = new Telegraf(BOT_TOKEN);

// Обработка команды /start
bot.command('start', (ctx) => {
    ctx.reply('✅ Бот работает!\n\nЯ получил твое сообщение через polling mode.');
    console.log('Получено сообщение от:', ctx.from.username || ctx.from.id);
});

// Обработка любого текста
bot.on('text', (ctx) => {
    ctx.reply(`Ты написал: "${ctx.message.text}"`);
});

// Запуск в режиме polling (не требует HTTPS)
console.log('🤖 Бот запускается в режиме polling...');
bot.launch();

// Обработка завершения
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));