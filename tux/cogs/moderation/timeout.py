import discord
from discord.ext import commands

from prisma.enums import CaseType
from tux.bot import Tux
from tux.utils import checks
from tux.utils.flags import TimeoutFlags, generate_usage
from tux.utils.functions import parse_time_string

from . import ModerationCogBase


class Timeout(ModerationCogBase):
    def __init__(self, bot: Tux) -> None:
        super().__init__(bot)
        self.timeout.usage = generate_usage(self.timeout, TimeoutFlags)

    @commands.hybrid_command(
        name="timeout",
        aliases=["t", "to", "mute", "m"],
    )
    @commands.guild_only()
    @checks.has_pl(2)
    async def timeout(
        self,
        ctx: commands.Context[Tux],
        member: discord.Member,
        reason: str | None = None,
        *,
        flags: TimeoutFlags,
    ) -> None:
        """
        Timeout a member from the server.

        Parameters
        ----------
        ctx : commands.Context[Tux]
            The context in which the command is being invoked.
        member : discord.Member
            The member to timeout.
        reason : str | None
            The reason for the timeout.
        flags : TimeoutFlags
            The flags for the command (duration: str, silent: bool).

        Raises
        ------
        discord.DiscordException
            If an error occurs while timing out the user.
        """
        assert ctx.guild

        # Check if member is already timed out
        if member.is_timed_out():
            await ctx.send(f"{member} is already timed out.", ephemeral=True)
            return

        # Check if moderator has permission to timeout the member
        if not await self.check_conditions(ctx, member, ctx.author, "timeout"):
            return

        final_reason = reason or self.DEFAULT_REASON
        duration = parse_time_string(flags.duration)

        # Execute timeout with case creation and DM
        await self.execute_mod_action(
            ctx=ctx,
            case_type=CaseType.TIMEOUT,
            user=member,
            final_reason=final_reason,
            silent=flags.silent,
            dm_action=f"timed out for {flags.duration}",
            actions=[(member.timeout(duration, reason=final_reason), type(None))],
            duration=flags.duration,
        )


async def setup(bot: Tux) -> None:
    await bot.add_cog(Timeout(bot))
