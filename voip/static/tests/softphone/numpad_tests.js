/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { nextTick, triggerHotkey } from "@web/../tests/helpers/utils";
import { click, contains, insertText } from "@web/../tests/utils";

QUnit.module("numpad");

QUnit.test("Number input is focused when opening the numpad.", async () => {
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button[title='Open Numpad']");
    await contains("input[placeholder='Enter the number…']:focus");
});

QUnit.test(
    "Number input content is persisted when closing then re-opening the numpad.",
    async () => {
        start();
        await click(".o_menu_systray button[title='Open Softphone']");
        await click("button[title='Open Numpad']");
        await insertText("input[placeholder='Enter the number…']", "513");
        await click("button[title='Close Numpad']");
        await click("button[title='Open Numpad']");
        await contains("input[placeholder='Enter the number…']", { value: "513" });
    }
);

QUnit.test(
    "Clicking on the “Backspace button” deletes the last character of the number input.",
    async () => {
        start();
        await click(".o_menu_systray button[title='Open Softphone']");
        await click("button[title='Open Numpad']");
        await insertText("input[placeholder='Enter the number…']", "123");
        await click("button[title='Backspace']");
        await nextTick();
        await contains("input[placeholder='Enter the number…']", { value: "12" });
    }
);

QUnit.test("Clicking on a key appends it to the number input.", async () => {
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button[title='Open Numpad']");
    await insertText("input[placeholder='Enter the number…']", "123");
    await click("button", { text: "#" });
    await nextTick();
    await contains("input[placeholder='Enter the number…']", { value: "123#" });
});

QUnit.test("Number input is focused after clicking on a key.", async () => {
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button[title='Open Numpad']");
    await click("button", { text: "2" });
    await nextTick();
    await contains("input[placeholder='Enter the number…']:focus");
});

QUnit.test("Pressing Enter in the input makes a call to the dialed number.", async (assert) => {
    const pyEnv = await startServer();
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button[title='Open Numpad']");
    await contains("input[placeholder='Enter the number…']");
    await insertText("input[placeholder='Enter the number…']", "9223372036854775807");
    await triggerHotkey("Enter");
    assert.strictEqual(
        pyEnv["voip.call"].searchCount([["phone_number", "=", "9223372036854775807"]]),
        1
    );
});

QUnit.test(
    "Pressing Enter in the input doesn't make a call if the trimmed input is empty string.",
    async (assert) => {
        const pyEnv = await startServer();
        start();
        await click(".o_menu_systray button[title='Open Softphone']");
        await click("button[title='Open Numpad']");
        await insertText("input[placeholder='Enter the number…']", "\t \n\r\v");
        await triggerHotkey("Enter");
        assert.strictEqual(pyEnv["voip.call"].searchCount([]), 0);
    }
);
