"""Simple CLI for Alpha AI."""

import sys
import json
import click
import httpx
from typing import Optional

from .settings import settings


@click.group()
@click.option('--base-url', default=f"http://localhost:8100{settings.api_v1_prefix}", 
              help='Base URL for Alpha AI server')
@click.pass_context
def cli(ctx, base_url):
    """Alpha AI command line interface."""
    ctx.ensure_object(dict)
    ctx.obj['base_url'] = base_url


@cli.command()
@click.pass_context
def model(ctx):
    """Get the current model."""
    base_url = ctx.obj['base_url']
    try:
        response = httpx.get(f"{base_url}/model")
        response.raise_for_status()
        data = response.json()
        click.echo(f"Current model: {data['model']}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('model_name')
@click.pass_context
def set_model(ctx, model_name):
    """Set the model."""
    base_url = ctx.obj['base_url']
    try:
        response = httpx.post(f"{base_url}/model", json={"model": model_name})
        response.raise_for_status()
        data = response.json()
        click.echo(f"Model changed to: {data['model']}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('message')
@click.pass_context
def chat(ctx, message):
    """Send a chat message."""
    base_url = ctx.obj['base_url']
    try:
        response = httpx.post(f"{base_url}/chat", json={"message": message}, timeout=30.0)
        response.raise_for_status()
        data = response.json()
        click.echo(f"\n{data['response']}\n")
        if click.get_current_context().find_root().params.get('verbose'):
            click.echo(f"[Model: {data['model']}, Tokens: {data['usage']['total_tokens']}]")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--limit', default=10, help='Number of messages to show')
@click.pass_context
def history(ctx, limit):
    """Show conversation history."""
    base_url = ctx.obj['base_url']
    try:
        response = httpx.get(f"{base_url}/conversation", params={"limit": limit})
        response.raise_for_status()
        data = response.json()
        
        click.echo(f"\n=== Conversation History ({data['total_messages']} messages) ===\n")
        
        for msg in data['messages']:
            role = msg['role'].upper()
            if role == "USER":
                click.secho(f"{role}: {msg['content']}", fg='blue')
            else:
                click.secho(f"{role}: {msg['content']}", fg='green')
            click.echo("")
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def clear(ctx):
    """Clear conversation history."""
    base_url = ctx.obj['base_url']
    try:
        response = httpx.delete(f"{base_url}/conversation")
        response.raise_for_status()
        data = response.json()
        click.echo(f"Conversation cleared. Current model: {data['model']}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()