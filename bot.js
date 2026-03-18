import { Telegraf, Markup } from 'telegraf';

const BOT_TOKEN = process.env.TELEGRAM_TOKEN;
const APP_URL   = process.env.MINI_APP_URL || 'https://egg-launcher-miniapp.vercel.app';
const API_URL   = process.env.API_URL       || 'https://egg-api-production.up.railway.app';

const bot = new Telegraf(BOT_TOKEN);

const openBtn = Markup.inlineKeyboard([
  [Markup.button.webApp('ðŸ¥š Open Egg Launcher', APP_URL)],
]);

bot.start(async (ctx) => {
  const user = ctx.from;
  // Auto-create wallet on /start
  try {
    await fetch(`${API_URL}/api/wallet/${user.id}?username=${user.username || ''}`)
  } catch {}

  await ctx.reply(
    `ðŸ¥š *Egg Launcher*\n\nThe living launchpad on TON.\n\n` +
    `â€¢ Launch a token in 60 seconds\n` +
    `â€¢ Bonding curve â€” no rug possible\n` +
    `â€¢ 0.2% creator fees on every trade\n` +
    `â€¢ Graduates to DeDust at 500 TON\n\n` +
    `_1 TON to launch. Earn forever._`,
    { parse_mode: 'Markdown', ...openBtn }
  );
});

bot.command('wallet', async (ctx) => {
  try {
    const user = ctx.from;
    const r = await fetch(`${API_URL}/api/wallet/${user.id}?username=${user.username || ''}`);
    const data = await r.json();
    await ctx.reply(
      `ðŸ’³ *Your Egg Wallet*\n\n` +
      `Address:\n\`${data.address}\`\n\n` +
      `Balance: *${parseFloat(data.balance).toFixed(4)} TON*\n\n` +
      `_Fund this address to buy tokens inside the app._\n` +
      `_Type /seed to export your private keys._`,
      { parse_mode: 'Markdown' }
    );
  } catch (e) {
    ctx.reply('Error fetching wallet: ' + e.message);
  }
});

bot.command('seed', async (ctx) => {
  try {
    const user = ctx.from;
    const { data } = await (await import('@supabase/supabase-js'))
      .createClient(process.env.SUPABASE_URL, process.env.SUPABASE_KEY)
      .from('egg_wallets').select('mnemonic').eq('tg_id', user.id).single();

    if (!data) return ctx.reply('No wallet found. Send /start first.');

    await ctx.reply(
      `ðŸ”‘ *Your Seed Phrase*\n\n` +
      `\`${data.mnemonic}\`\n\n` +
      `âš ï¸ *Keep this secret!* Anyone with these words can access your wallet.\n` +
      `Import into any TON wallet (Tonkeeper, MyTonWallet) using this 24-word phrase.`,
      { parse_mode: 'Markdown' }
    );
  } catch (e) {
    ctx.reply('Error: ' + e.message);
  }
});

bot.command('dashboard', async (ctx) => {
  try {
    const r = await fetch(`${API_URL}/api/dashboard`);
    const d = await r.json();
    await ctx.reply(
      `ðŸ“Š *Egg Launcher Stats*\n\n` +
      `ðŸª™ Tokens launched: *${d.total}*\n` +
      `ðŸŽ“ Graduated: *${d.graduated}*\n` +
      `ðŸ’Ž Treasury: *${d.treasury_ton?.toFixed(2)} TON*`,
      { parse_mode: 'Markdown', ...openBtn }
    );
  } catch {
    ctx.reply('Stats unavailable.', openBtn);
  }
});

bot.command('launch',    ctx => ctx.reply('Ready to launch? ðŸš€', openBtn));
bot.command('trending',  ctx => ctx.reply('See what\'s trending ðŸ”¥', openBtn));

bot.on('new_chat_members', async (ctx) => {
  const m = ctx.message.new_chat_members[0];
  if (m.id === ctx.botInfo.id) return;
  await ctx.reply(
    `ðŸ¥š Welcome @${m.username || m.first_name}!\n\nLaunch your token on *Egg Launcher*`,
    { parse_mode: 'Markdown', ...openBtn }
  ).catch(() => {});
});

bot.launch();
console.log('ðŸ¥š Egg Launcher bot running...');
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));
