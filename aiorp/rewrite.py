import yarl


class Rewrite:
    """Specifies a rewrite configuration for rewriting URL paths.

    This class defines a path rewriting rule that can be used to modify
    the path of incoming requests before they are proxied.

    Args:
        rfrom: The path pattern to match and replace.
        rto: The replacement path pattern.

    Raises:
        ValueError: If only one of rfrom or rto is provided.
    """

    def __init__(self, rfrom: str, rto: str):
        """Initialize the rewrite configuration.

        Args:
            rfrom: The path pattern to match and replace.
            rto: The replacement path pattern.

        Raises:
            ValueError: If only one of rfrom or rto is provided.
        """
        self.rfrom = rfrom
        self.rto = rto

    def execute(self, url: yarl.URL):
        """Rewrite the path of the request URL from current to new value.

        Args:
            url: The url to apply the rewrite to
        """
        return url.with_path(url.path.replace(self.rfrom, self.rto))
