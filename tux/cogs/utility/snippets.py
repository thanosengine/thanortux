import datetime
import string

import discord
from discord import AllowedMentions
from discord.ext import commands
from loguru import logger

from prisma.models import Snippet
from tux.database.controllers import DatabaseController
from tux.utils.embeds import EmbedCreator


class Snippets(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.db = DatabaseController().snippet
        self.config = DatabaseController().guild_config

    @commands.command(
        name="snippets",
        aliases=["ls"],
        usage="$snippets <page>",
    )
    @commands.guild_only()
    async def list_snippets(self, ctx: commands.Context[commands.Bot], page: int = 1) -> None:
        """
        List snippets by page.

        Parameters
        ----------
        ctx : commands.Context[commands.Bot]
            The context object.
        page : int, optional
            The page number, by default 1.
        """

        if ctx.guild is None:
            await ctx.send("This command cannot be used in direct messages.")
            return

        snippets: list[Snippet] = await self.db.get_all_snippets_sorted(newestfirst=True)

        # remove snippets that are not in the current server
        snippets = [snippet for snippet in snippets if snippet.guild_id == ctx.guild.id]

        # Calculate the number of pages based on the number of snippets
        pages = 1 if len(snippets) <= 10 else len(snippets) // 10 + 1

        # If there are no snippets, send an error message
        if not snippets:
            embed = EmbedCreator.create_error_embed(
                title="Error",
                description="No snippets found.",
                ctx=ctx,
            )
            await ctx.send(embed=embed, delete_after=5)
            return

        # If the page number is invalid, send an error message
        if page < 1 or page > pages:
            embed = EmbedCreator.create_error_embed(
                title="Error",
                description="Invalid page number.",
                ctx=ctx,
            )
            await ctx.send(embed=embed)
            return

        # Get the snippets for the specified page
        snippets = snippets[(page - 1) * 10 : page * 10]

        # Snippets:
        # `01. snippet_name        | author: author_name`
        # `02. longer_snippet_name | author: author_name`

        embed = EmbedCreator.create_info_embed(
            title="Snippets",
            description="\n".join(
                [
                    f"`{str(index + 1).zfill(2)}. {snippet.snippet_name.ljust(20)} | author: {self.bot.get_user(snippet.snippet_user_id) or 'Unknown'}`"
                    for index, snippet in enumerate(snippets)
                ],
            ),
            ctx=ctx,
        )
        embed.set_footer(text=f"Page {page}/{pages}")

        await ctx.send(embed=embed)

    @commands.command(
        name="deletesnippet",
        aliases=["ds"],
        usage="$deletesnippet [name]",
    )
    @commands.guild_only()
    async def delete_snippet(self, ctx: commands.Context[commands.Bot], name: str) -> None:
        """
        Delete a snippet by name.

        Parameters
        ----------
        ctx : commands.Context[commands.Bot]
            The context object.
        name : str
            The name of the snippet.
        """

        if ctx.guild is None:
            await ctx.send("This command cannot be used in direct messages.")
            return

        snippet = await self.db.get_snippet_by_name_and_guild_id(name, ctx.guild.id)

        if snippet is None:
            embed = EmbedCreator.create_error_embed(
                title="Error",
                description="Snippet not found.",
                ctx=ctx,
            )
            await ctx.send(embed=embed, delete_after=5)
            return

        # Check if the author of the snippet is the same as the user who wants to delete it and if theres no author don't allow deletion

        # TODO: this was quick and dirty, needs to be refactored

        author_id = snippet.snippet_user_id or 0
        if author_id != ctx.author.id:
            conf = await self.config.get_guild_config(ctx.guild.id)
            user_roles = [role.id for role in ctx.author.roles]  # type: ignore

            if not conf:
                embed = EmbedCreator.create_error_embed(
                    title="Error",
                    description="You can only delete your own snippets.",
                    ctx=ctx,
                )
                await ctx.send(embed=embed)
                return

            if all(role not in user_roles for role in conf.perm_level_9_role_id):
                embed = EmbedCreator.create_error_embed(
                    title="Error",
                    description="You can only delete your own snippets.",
                    ctx=ctx,
                )
                await ctx.send(embed=embed)
                return

        await self.db.delete_snippet_by_id(snippet.snippet_id)

        await ctx.send("Snippet deleted.")
        logger.info(f"{ctx.author} deleted the snippet with the name {name}.")

    @commands.command(
        name="snippet",
        aliases=["s"],
        usage="$snippet [name]",
    )
    @commands.guild_only()
    async def get_snippet(self, ctx: commands.Context[commands.Bot], name: str) -> None:
        """
        Get a snippet by name.

        Parameters
        ----------
        ctx : commands.Context[commands.Bot]
            The context object.
        name : str
            The name of the snippet.
        """

        if ctx.guild is None:
            await ctx.send("This command cannot be used in direct messages.")
            return

        snippet = await self.db.get_snippet_by_name_and_guild_id(name, ctx.guild.id)

        if snippet is None:
            embed = EmbedCreator.create_error_embed(
                title="Error",
                description="Snippet not found.",
                ctx=ctx,
            )
            await ctx.send(embed=embed, delete_after=5)
            return

        text = f"`/snippets/{snippet.snippet_name}.txt` || {snippet.snippet_content}"

        await ctx.send(text, allowed_mentions=AllowedMentions.none())

    @commands.command(
        name="snippetinfo",
        aliases=["si"],
        usage="$snippetinfo [name]",
    )
    @commands.guild_only()
    async def get_snippet_info(self, ctx: commands.Context[commands.Bot], name: str) -> None:
        """
        Get information about a snippet by name.

        Parameters
        ----------
        ctx : commands.Context[commands.Bot]
            The context object.
        name : str
            The name of the snippet.
        """

        if ctx.guild is None:
            await ctx.send("This command cannot be used in direct messages.")
            return

        snippet = await self.db.get_snippet_by_name_and_guild_id(name, ctx.guild.id)

        if snippet is None:
            embed = EmbedCreator.create_error_embed(
                title="Error",
                description="Snippet not found.",
                ctx=ctx,
            )
            await ctx.send(embed=embed, delete_after=5)
            return

        author = self.bot.get_user(snippet.snippet_user_id) or ctx.author

        embed: discord.Embed = EmbedCreator.custom_footer_embed(
            title="Snippet Information",
            content=f"**Name:** {snippet.snippet_name}\n**Author:** {author}\n**Created At:** (set as embed timestamp)\n**Content:** {snippet.snippet_content}",
            ctx=ctx,
            latency="N/A",
            interaction=None,
            state="DEBUG",
            user=author,
        )

        embed.timestamp = snippet.snippet_created_at or datetime.datetime.fromtimestamp(
            0,
            datetime.UTC,
        )

        await ctx.send(embed=embed)

    @commands.command(
        name="createsnippet",
        aliases=["cs"],
        usage="$createsnippet [name] [content]",
    )
    @commands.guild_only()
    async def create_snippet(self, ctx: commands.Context[commands.Bot], *, arg: str) -> None:
        """
        Create a snippet.

        Parameters
        ----------
        ctx : commands.Context[commands.Bot]
            The context object.
        arg : str
            The name and content of the snippet.
        """

        if ctx.guild is None:
            await ctx.send("This command cannot be used in direct messages.")
            return

        args = arg.split(" ")
        if len(args) < 2:
            embed = EmbedCreator.create_error_embed(
                title="Error",
                description="Please provide a name and content for the snippet.",
                ctx=ctx,
            )
            await ctx.send(embed=embed)
            return

        name = args[0]
        content = " ".join(args[1:])
        created_at = datetime.datetime.now(datetime.UTC)
        author_id = ctx.author.id
        server_id = ctx.guild.id

        # Check if the snippet already exists
        if await self.db.get_snippet_by_name_and_guild_id(name, ctx.guild.id) is not None:
            embed = EmbedCreator.create_error_embed(
                title="Error",
                description="Snippet already exists.",
                ctx=ctx,
            )
            await ctx.send(embed=embed)
            return

        # Check if the name is longer than 20 characters and includes non-alphanumeric characters (except -_)
        rules = set(string.ascii_letters + string.digits + "-_")

        if len(name) > 20 or any(char not in rules for char in name):
            embed = EmbedCreator.create_error_embed(
                title="Error",
                description="Snippet name must be alphanumeric (allows dashes and underscores) and less than 20 characters.",
            )
            await ctx.send(embed=embed)
            return

        await self.db.create_snippet(
            snippet_name=name,
            snippet_content=content,
            snippet_created_at=created_at,
            snippet_user_id=author_id,
            guild_id=server_id,
        )

        await ctx.send("Snippet created.")
        logger.info(f"{ctx.author} created a snippet with the name {name} and content {content}.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Snippets(bot))
