# mediawiki-matrix-bot


A Bot which publishes mediawiki Recent Changes from the [`api.php` endpoint](https://wiki.nixos.org/w/api.php?action=help&modules=query%2Brecentchanges) to a Matrix room or a Signal group.

## Configuration with `config.json`

### Common Options

#### `type`

The output type for messages. Supported values:
- `"matrix"` (default) - Send messages to a Matrix room
- `"signal"` - Send messages to a Signal group via the [signal-cli-rest-api](https://github.com/bbernhard/signal-cli-rest-api)

#### `baseurl`

The baseurl is the the domain and path of the mediawiki server, e.g.
`https://wiki.nixos.org`

#### `api_path`
The default path to the api is `{baseurl}/api.php`. If the api endpoint is not
at the default location like in wiki.nixos.org it can be set to `/w/api.php` to
query a different endpoint.

#### `timeout`
The polling interval in seconds for checking recent changes. Default: `60`

### Matrix Configuration

When `type` is `"matrix"` (or omitted), the following options are required:

| Option | Description |
|--------|-------------|
| `server` | The Matrix homeserver URL, e.g. `https://matrix.org` |
| `mxid` | The Matrix user ID for the bot, e.g. `@botname:matrix.org` |
| `password` | The password for the bot account |
| `room` | The Matrix room ID to send messages to, e.g. `!roomid:matrix.org` |

Example: See `config.json.example`

### Signal Configuration

When `type` is `"signal"`, the following options are required:

| Option | Description |
|--------|-------------|
| `signal_api_url` | The URL of the signal-cli-rest-api, e.g. `http://localhost:8080` |
| `signal_source_number` | The registered phone number to send from, e.g. `+1234567890` |
| `signal_target_group` | The Signal group ID to send messages to |

Signal messages use styled text formatting with **bold**, *italic*, and `monospace` instead of HTML colors.

Example: See `config.signal.json.example`


## Development

```
$ nix-build
$ ./result/bin/mediawiki-matrix-bot config.json
```

## License
MIT
