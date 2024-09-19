import pydantic
from slack_sdk.models.blocks import (
    Block,
    SectionBlock,
    DividerBlock,
    PlainTextObject,
    ButtonElement,
)


class SlackNotification(pydantic.BaseModel):
    blocks: list[dict] = []

    def add_block(self, block: Block):
        self.blocks.append(block.to_dict())

    def add_combined_block(
            self,
            build_info: dict,
            network: str,
            failed_tests: str,
            report_url: str,
            comments: list[str],
    ):
        fields = [
            {"text": "*Failed build*", "type": "mrkdwn"},
            {"text": f"<{build_info['url']}|`{build_info['id']}`>", "type": "mrkdwn"},
            {"text": "*Network*", "type": "mrkdwn"},
            {"text": network, "type": "mrkdwn"},
        ]

        if failed_tests:
            fields.extend([
                {"text": "*Failed Tests*", "type": "mrkdwn"},
                {"text": failed_tests, "type": "mrkdwn"}
            ])

        for index, comment in enumerate(comments):
            if comment:
                number = f" {index + 1}" if len(comments) > 1 else ""
                fields.extend([
                    {"text": f"*Comment{number}*", "type": "mrkdwn"},
                    {"text": comment, "type": "mrkdwn"}
                ])

        accessory = ButtonElement(text=PlainTextObject(text="VIEW REPORT"), url=report_url) if report_url else None
        block = SectionBlock(fields=fields, accessory=accessory)
        self.add_block(block)

    def add_divider(self):
        block = DividerBlock()
        self.add_block(block)