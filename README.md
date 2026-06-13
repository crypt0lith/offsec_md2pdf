# OffSec Exam Report Markdown-to-PDF

Render an OffSec exam report markdown file to a PDF.

A markdown template for the OSCP exam report is included [here](https://github.com/crypt0lith/OffsecExamReport_md2pdf/blob/master/example/OSCP-Exam-Template.md).
See [example/OSCP-OS-12345678-Exam-Report.pdf](https://raw.githubusercontent.com/crypt0lith/OffsecExamReport_md2pdf/master/example/OSCP-OS-12345678-Exam-Report.pdf) for the output PDF.

## Usage

```
offsec_md2pdf.py [-o DIRNAME | -O FILE]
                 [--cert CERT] [--osid OSID] [--email EMAIL]
                 [--accent COLOR] [--background COLOR]
                 [--normalize-slugs] [--content-dir DIRNAME]
                 FILE

positional arguments:
  FILE                  markdown report file

output options:
  -o, --outdir DIRNAME  path to output directory
  -O, --outfile FILE    output PDF path

candidate options:
  each option, if not specified as an argument, can also be present in the markdown yaml frontmatter.
  '--cert' and '--osid' will be inferred from '--outfile' then FILE if unspecified via args / frontmatter,
  and if those path's basenames match the pattern '<CERT>-OS-<OSID>'

  --cert CERT           certification shortname, e.g. 'OSCP' (choices: OSCP, OSWP, OSWA, OSDA, OSWE, OSEP, OSED, OSEE, OSIR, OSTH)
  --osid OSID           candidate OSID, e.g. 'OS-12345'
  --email EMAIL         candidate email

rendering options:
  each option, if not specified as an argument, can also be present in the markdown yaml frontmatter

  --accent COLOR        accent color (default: #a76bf9)
  --background COLOR    title page background color (default: #0e1116)

markdown options:
  --normalize-slugs     convert Obsidian-style anchor links to python-markdown slugs
  --content-dir DIRNAME
                        base directory for relative image paths
```

### Installation / Example Usage

```shell
git clone https://github.com/crypt0lith/OffsecExamReport_md2pdf.git
cd ./OffsecExamReport_md2pdf
uv run offsec_md2pdf.py /path/to/OSCP-OS-XXXXXX-Exam-Report.md -o /path/to/outdir
```

If you do not use [`uv`](https://docs.astral.sh/uv/getting-started/installation/), `requirements.txt` has also been provided.

