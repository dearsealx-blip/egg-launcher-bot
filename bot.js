// Egg Launcher Telegram Bot
import { Telegraf, Markup } from 'telegraf';

const BOT_TOKEN = process.env.TELEGRAM_TOKEN;
const APP_URL   = process.env.MINI_APP_URL || 'https://egg-launcher.vercel.app';
const API_URL   = process.env.API_URL       || 'https://egg-api-production.up.railway.app';

const bot = new Telegraf(BOT_TOKEN);

const openBtn = Markup.inlineKeyboard([
  Markup.button.webApp('🥚 Open Launcher', APP_URL),
]);

bot.start(async (ctx) => {
  await ctx.replyWithPhoto(
    { url: 'https://i.imgur.com/placeholder.png' },
    {
      caption: `*🥚 Egg Launcher*\n\nThe living launchpad on TON.\n\n` +
        `• Launch a token in 60 seconds\n` +
        `• Bonding curve AMM — no rug\n` +
        `• 0.2% creator fees forever\n` +
        `• Graduates to DeDust or STON.fi at 500 TON\n\n` +
        `_1 TON launch fee_`,
      parse_mode: 'Markdown',
      ...openBtn,
    }
  ).catch(() => ctx.reply(
    `🥚 *Egg Launcher*\n\nThe living launchpad on TON.`,
    { parse_mode: 'Markdown', ...openBtn }
  ));
});

bot.command('launch',    ctx => ctx.reply('🚀 Ready to launch?', openBtn));
bot.command('trending',  ctx => ctx.reply('🔥 See what\'s trending:', openBtn));
bot.command('portfolio', ctx => ctx.reply('👤 Your portfolio:', openBtn));

bot.command('dashboard', async (ctx) => {
  try {
    const r = await fetch(`${API_URL}/api/dashboard`);
    const d = await r.json();
    await ctx.reply(
      `📊 *Egg Launcher Stats*\n\n` +
      `🪙 Tokens launched: *${d.total}*\n` +
      `🎓 Graduated: *${d.graduated}*\n` +
      `💎 Treasury: *${d.treasury_ton?.toFixed(2)} TON*\n` +
      (d.top_token ? `\n🏆 Top token: *$${d.top_token.ticker}* (${d.top_token.real_ton?.toFixed(1)} TON)` : ''),
      { parse_mode: 'Markdown', ...openBtn }
    );
  } catch {
    ctx.reply('Stats unavailable right now.', openBtn);
  }
});

// Handle new chat members — welcome with launcher button
bot.on('new_chat_members', async (ctx) => {
  const newMember = ctx.message.new_chat_members[0];
  if (newMember.id === ctx.botInfo.id) return; // bot joining
  await ctx.reply(
    `👋 Welcome @${newMember.username || newMember.first_name}!\n\nLaunch your token on *Egg Launcher* 🥚`,
    { parse_mode: 'Markdown', ...openBtn }
  );
});

bot.launch();
console.log('🥚 Egg Launcher bot running...');

process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));
