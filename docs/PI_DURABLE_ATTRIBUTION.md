# Pi Durable audit and attribution

Reference revision: 273b79bb8d3d8907cae9fbd6abd3da163ee2a343 of https://github.com/disler/pi-durable-news-agent.

Inspected apps/dna-server-api/src/agents/tools/jev-classify.ts, src/news/hfs.ts and the MIT license. The six decision concepts, separate HFS dimensions, logged decisions and durable-state ideas are adapted independently in Python. No upstream executable code was copied. No native JEV/SystemOne dependency is selected: the user correction requires the single configurable OpenAI chat interface. Existing Horizon program Laya code remains separate.

Upstream license:

```text
MIT License

Copyright (c) 2026 IndyDevDan

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
