import subprocess
import zipfile
from xml.sax.saxutils import escape
from datetime import date
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "著作权材料"
IMG_DIR = OUT_DIR / "截图"
SOFTWARE_NAME = "用于多模态生理信号的分析系统"
VERSION = "V1.0"


def rtf_escape(text: str) -> str:
    parts = []
    for ch in text:
        code = ord(ch)
        if ch == "\\":
            parts.append("\\\\")
        elif ch == "{":
            parts.append("\\{")
        elif ch == "}":
            parts.append("\\}")
        elif ch == "\n":
            parts.append("\\par\n")
        elif ch == "\t":
            parts.append("\\tab ")
        elif 32 <= code <= 126:
            parts.append(ch)
        else:
            signed = code if code < 32768 else code - 65536
            parts.append(f"\\u{signed}?")
    return "".join(parts)


class RtfBuilder:
    def __init__(self):
        self.parts = [
            r"{\rtf1\ansi\ansicpg936\deff0",
            r"{\fonttbl",
            r"{\f0\fnil\fcharset134 Hiragino Sans GB;}",
            r"{\f1\fnil\fcharset0 Times New Roman;}",
            r"{\f2\fmodern\fcharset0 Courier New;}",
            r"}",
            r"\viewkind4\uc1",
            "\n",
        ]

    def raw(self, text: str):
        self.parts.append(text)
        if not text.endswith("\n"):
            self.parts.append("\n")

    def paragraph(
        self,
        text: str = "",
        *,
        font: int = 0,
        size: int = 24,
        bold: bool = False,
        align: str = "left",
        first_line: int = 0,
        left_indent: int = 0,
        space_before: int = 0,
        space_after: int = 160,
        line_spacing: int = 360,
    ):
        align_map = {"left": r"\ql", "center": r"\qc", "right": r"\qr", "justify": r"\qj"}
        bold_flag = r"\b" if bold else ""
        indent = f"\\li{left_indent}" if left_indent else ""
        first = f"\\fi{first_line}" if first_line else ""
        self.parts.append(
            rf"\pard{align_map.get(align, r'\ql')}\sb{space_before}\sa{space_after}\sl{line_spacing}\slmult1{indent}{first}\f{font}\fs{size}{bold_flag} "
            + rtf_escape(text)
            + r"\par"
            + "\n"
        )

    def page_break(self):
        self.parts.append(r"\page" + "\n")

    def image(self, path: Path, *, width_inches: float = 6.2):
        img = Image.open(path)
        picw, pich = img.size
        width_twips = int(width_inches * 1440)
        height_twips = int(width_twips * pich / picw)
        hexdata = path.read_bytes().hex().upper()
        self.parts.append(r"\pard\qc\sa160" + "\n")
        self.parts.append(
            r"{\pict\pngblip"
            + f"\\picw{picw}\\pich{pich}\\picwgoal{width_twips}\\pichgoal{height_twips}\n"
            + hexdata
            + "}\n"
        )
        self.parts.append(r"\par" + "\n")

    def code_block(self, text: str):
        for raw_line in text.splitlines():
            leading = len(raw_line) - len(raw_line.lstrip(" "))
            prefix = "\\~" * leading
            body = rtf_escape(raw_line[leading:])
            self.parts.append(rf"\pard\ql\li360\sa0\sb0\f2\fs16 {prefix}{body}\par" + "\n")
        if not text.splitlines():
            self.parts.append(r"\pard\ql\li360\sa0\sb0\f2\fs16 \par" + "\n")
        self.parts.append(r"\pard\sa120\par" + "\n")

    def build(self) -> str:
        return "".join(self.parts) + "}"


def write_rtf(path: Path, content: str):
    path.write_text(content, encoding="ascii")


def convert_word(rtf_path: Path):
    docx_path = rtf_path.with_suffix(".docx")
    doc_path = rtf_path.with_suffix(".doc")
    subprocess.run(["textutil", "-convert", "docx", str(rtf_path), "-output", str(docx_path)], check=True)
    subprocess.run(["textutil", "-convert", "doc", str(rtf_path), "-output", str(doc_path)], check=True)


class DocxBuilder:
    def __init__(self):
        self.blocks = []
        self.images = []
        self.image_counter = 1

    def paragraph(
        self,
        text: str = "",
        *,
        font: str = "宋体",
        size_half_points: int = 24,
        bold: bool = False,
        align: str = "left",
        first_line: int = 0,
        left_indent: int = 0,
        space_before: int = 0,
        space_after: int = 160,
        line_spacing: int = 360,
    ):
        self.blocks.append(
            (
                "paragraph",
                {
                    "text": text,
                    "font": font,
                    "size": size_half_points,
                    "bold": bold,
                    "align": align,
                    "first_line": first_line,
                    "left_indent": left_indent,
                    "space_before": space_before,
                    "space_after": space_after,
                    "line_spacing": line_spacing,
                },
            )
        )

    def page_break(self):
        self.blocks.append(("page_break", {}))

    def image(self, path: Path, *, width_inches: float = 6.5):
        self.blocks.append(("image", {"path": path, "width_inches": width_inches}))

    def code_block(self, text: str):
        for line in text.splitlines():
            self.paragraph(
                line,
                font="Courier New",
                size_half_points=18,
                space_after=0,
                line_spacing=240,
            )
        self.paragraph("", font="Courier New", size_half_points=18, space_after=120, line_spacing=240)

    @staticmethod
    def _align_xml(align: str) -> str:
        align_map = {"left": "left", "center": "center", "right": "right", "justify": "both"}
        return f'<w:jc w:val="{align_map.get(align, "left")}"/>'

    @staticmethod
    def _rpr(font: str, size: int, bold: bool) -> str:
        bold_xml = "<w:b/>" if bold else ""
        return (
            "<w:rPr>"
            f'<w:rFonts w:ascii="{escape(font)}" w:hAnsi="{escape(font)}" w:eastAsia="{escape(font)}"/>'
            f"<w:sz w:val=\"{size}\"/><w:szCs w:val=\"{size}\"/>{bold_xml}"
            "</w:rPr>"
        )

    def _paragraph_xml(self, spec: dict) -> str:
        ppr = (
            "<w:pPr>"
            f"{self._align_xml(spec['align'])}"
            f'<w:spacing w:before="{spec["space_before"]}" w:after="{spec["space_after"]}" w:line="{spec["line_spacing"]}" w:lineRule="auto"/>'
        )
        if spec["first_line"] or spec["left_indent"]:
            ppr += f'<w:ind w:firstLine="{spec["first_line"]}" w:left="{spec["left_indent"]}"/>'
        ppr += "</w:pPr>"
        text = escape(spec["text"])
        return (
            "<w:p>"
            + ppr
            + "<w:r>"
            + self._rpr(spec["font"], spec["size"], spec["bold"])
            + f'<w:t xml:space="preserve">{text}</w:t>'
            + "</w:r>"
            + "</w:p>"
        )

    def _page_break_xml(self) -> str:
        return "<w:p><w:r><w:br w:type=\"page\"/></w:r></w:p>"

    def _image_xml(self, path: Path, width_inches: float) -> str:
        img = Image.open(path)
        width_px, height_px = img.size
        cx = int(width_inches * 914400)
        cy = int(cx * height_px / width_px)
        rid = f"rId{len(self.images) + 1}"
        media_name = f"image{self.image_counter}{path.suffix.lower()}"
        self.image_counter += 1
        self.images.append((rid, media_name, path))

        return f"""
<w:p>
  <w:pPr><w:jc w:val="center"/><w:spacing w:after="160"/></w:pPr>
  <w:r>
    <w:drawing>
      <wp:inline distT="0" distB="0" distL="0" distR="0"
        xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
        xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
        xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
        <wp:extent cx="{cx}" cy="{cy}"/>
        <wp:docPr id="{len(self.images)}" name="{escape(media_name)}"/>
        <wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>
        <a:graphic>
          <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
            <pic:pic>
              <pic:nvPicPr>
                <pic:cNvPr id="{len(self.images)}" name="{escape(media_name)}"/>
                <pic:cNvPicPr/>
              </pic:nvPicPr>
              <pic:blipFill>
                <a:blip r:embed="{rid}"/>
                <a:stretch><a:fillRect/></a:stretch>
              </pic:blipFill>
              <pic:spPr>
                <a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>
                <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
              </pic:spPr>
            </pic:pic>
          </a:graphicData>
        </a:graphic>
      </wp:inline>
    </w:drawing>
  </w:r>
</w:p>
""".strip()

    def save(self, docx_path: Path):
        body_xml = []
        for kind, payload in self.blocks:
            if kind == "paragraph":
                body_xml.append(self._paragraph_xml(payload))
            elif kind == "page_break":
                body_xml.append(self._page_break_xml())
            elif kind == "image":
                body_xml.append(self._image_xml(payload["path"], payload["width_inches"]))

        document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document
  xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
  xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
  xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
  xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
  <w:body>
    {''.join(body_xml)}
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="1440" w:right="1800" w:bottom="1440" w:left="1800"/>
    </w:sectPr>
  </w:body>
</w:document>"""

        rel_items = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
        for rid, media_name, _ in self.images:
            rel_items.append(
                f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{escape(media_name)}"/>'
            )
        rel_items.append("</Relationships>")
        document_rels = "".join(rel_items)

        content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="png" ContentType="image/png"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""

        root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""

        core_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:dcmitype="http://purl.org/dc/dcmitype/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{escape(SOFTWARE_NAME)}</dc:title>
  <dc:creator>Codex</dc:creator>
  <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{date.today().isoformat()}T00:00:00Z</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{date.today().isoformat()}T00:00:00Z</dcterms:modified>
</cp:coreProperties>"""

        app_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
 xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Codex</Application>
</Properties>"""

        with zipfile.ZipFile(docx_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", content_types)
            zf.writestr("_rels/.rels", root_rels)
            zf.writestr("word/document.xml", document_xml)
            zf.writestr("word/_rels/document.xml.rels", document_rels)
            zf.writestr("docProps/core.xml", core_xml)
            zf.writestr("docProps/app.xml", app_xml)
            for _, media_name, path in self.images:
                zf.write(path, f"word/media/{media_name}")


def build_manual_doc():
    b = DocxBuilder()
    today = date.today().isoformat()

    b.paragraph(SOFTWARE_NAME, size_half_points=36, bold=True, align="center", space_before=600, space_after=240)
    b.paragraph("软件说明书", size_half_points=32, bold=True, align="center", space_after=360)
    b.paragraph(f"版本号：{VERSION}", size_half_points=24, align="center", space_after=120)
    b.paragraph(f"生成日期：{today}", size_half_points=24, align="center", space_after=120)
    b.paragraph("", size_half_points=24, space_after=240)
    b.paragraph("本说明书依据现有项目代码、运行结果及模板结构整理形成，可直接用于软件著作权申报材料编制。", size_half_points=24, first_line=480, align="justify")
    b.page_break()

    b.paragraph("软件概述", size_half_points=28, bold=True, space_before=120, space_after=180)
    b.paragraph(
        "用于多模态生理信号的分析系统是一套面向脑电信号（EEG）、心电信号（ECG）和肌电信号（EMG）的本地分析软件。系统在保留原有数据加载、预处理和分析算法框架的基础上，新增了可视化前端界面，用户可以先在前端填写姓名、性别和年龄，再按步骤完成模态选择、CSV 数据拖拽导入、分析功能确认以及结果查看。系统通过前端服务桥接层调用现有分析流程，实现“前端引导操作 + 后端自动分析 + 终端日志与图像结果展示”的一体化工作方式。",
        first_line=480,
        align="justify",
    )
    b.paragraph(
        "本系统适用于科研实验、教学演示、生理状态评估、运动监测以及多模态生理数据处理等场景。对于脑电数据，系统支持五通道 CSV 文件导入，并在分析前完成多通道平均处理；对于心电和肌电数据，系统支持单通道 CSV 文件导入；系统会依据用户选择的模态自动列出默认分析功能，其中脑电对应频带功率分析，心电对应心率与 HRV 分析，肌电对应 FFT、STFT 及频域指标分析。分析完成后，前端界面会展示原有终端运行日志和自动生成的结果图像，便于用户直接查看分析过程与结果。",
        first_line=480,
        align="justify",
    )

    b.paragraph("一、模块介绍", size_half_points=28, bold=True, space_before=220, space_after=180)
    b.paragraph("1. 功能模块结构图", size_half_points=24, bold=True, space_after=120)
    b.image(IMG_DIR / "前端模块结构图.png", width_inches=7.0)
    b.paragraph("图1 前端模块结构图", align="center", size_half_points=22, space_after=180)

    module_items = [
        "登录信息模块：位于前端流程起点，负责采集用户姓名、性别和年龄信息，并在会话摘要区域中进行展示。",
        "数据导入模块：负责模态选择和 CSV 文件导入，支持拖拽上传；脑电要求导入 5 个 CSV 文件，心电和肌电各要求导入 1 个 CSV 文件。",
        "功能确认模块：根据用户选定的模态自动列出默认分析功能，保证前端展示逻辑与原有分析框架中的默认模块映射保持一致。",
        "前端服务桥接模块：负责会话管理、文件保存、状态轮询、日志回传和结果图片路径整理，并将前端操作转换为后端分析任务。",
        "数据加载模块：复用现有 LoadDataset 逻辑，读取上传目录中的 CSV 文件，解析时间戳和信号列，并完成模态识别、通道对齐和分段处理。",
        "预处理模块：复用现有 Preprocess 逻辑，对信号执行带通滤波和工频陷波处理，为后续分析提供稳定输入。",
        "分析调度与算法模块：复用现有 Analysis、BandAnalysis、Heartrate、FFT、STFT 和 FreqAnalysis 等模块，根据模态自动调用对应分析算法。",
        "结果展示模块：在前端界面中显示系统终端日志和自动生成的图像结果，使用户可以在同一界面中查看分析进度和输出图表。",
    ]
    b.paragraph("2. 各功能模块说明", size_half_points=24, bold=True, space_after=120)
    for idx, item in enumerate(module_items, start=1):
        b.paragraph(f"（{idx}）{item}", first_line=0, left_indent=0, align="justify")

    b.paragraph("二、流程介绍", size_half_points=28, bold=True, space_before=220, space_after=180)
    b.paragraph("1. 处理流程图", size_half_points=24, bold=True, space_after=120)
    b.image(IMG_DIR / "前端处理流程图.png", width_inches=6.2)
    b.paragraph("图6 前端处理流程图", align="center", size_half_points=22, space_after=180)

    flow_steps = [
        "用户打开前端界面，在登录界面填写姓名、性别和年龄信息，并点击“下一步”进入分析流程。",
        "用户在数据导入界面中先选择模态，然后按照提示拖拽上传对应数量的 CSV 文件，其中脑电为五通道数据，心电和肌电为单通道数据。",
        "系统在接收到上传文件后，根据所选模态自动生成默认分析功能列表，并在功能确认界面中展示给用户确认。",
        "用户点击“确定并开始分析”后，前端服务桥接层会将上传文件保存到会话目录，并调用现有分析流程执行数据加载、预处理和分析。",
        "后端算法沿用原有逻辑，完成模态识别、滤波处理和对应算法分析，同时将运行过程中的终端输出实时回传到前端界面。",
        "分析完成后，前端结果页展示系统终端运行日志以及生成的结果图像，用户可以在同一界面中查看分析过程与最终图表。",
    ]
    b.paragraph("2. 具体处理过程", size_half_points=24, bold=True, space_after=120)
    step_blocks = [
        (
            "步骤一：登录界面。用户打开系统后首先进入登录界面，在此填写姓名、性别和年龄信息。该界面不要求输入账号和密码，填写完成后点击“下一步”即可进入数据导入阶段。",
            "图2 前端步骤1 登录界面",
            "图1_前端步骤1_登录界面.png",
            6.9,
        ),
        (
            "步骤二：数据导入界面。用户先选择待分析模态，再拖拽对应数量的 CSV 文件到导入区域。系统会提示脑电为五通道数据，需要导入 5 个 CSV 文件；心电和肌电为单通道数据，各需要导入 1 个 CSV 文件。上传成功后，界面下方会显示已识别文件列表。",
            "图3 前端步骤2 数据导入界面",
            "图2_前端步骤2_数据导入界面.png",
            6.9,
        ),
        (
            "步骤三：功能确认界面。系统依据所选模态自动列出默认分析功能，用户只需核对当前功能列表是否符合预期，然后点击“确定并开始分析”进入执行阶段。该步骤保证前端逻辑与原有代码中的默认分析映射保持一致。",
            "图4 前端步骤3 功能确认界面",
            "图3_前端步骤3_功能确认界面.png",
            6.9,
        ),
        (
            "步骤四：执行与结果展示界面。系统调用现有分析流程后，会在左侧终端区域展示运行日志，在右侧结果区域展示生成的分析图像。用户可以从这一界面同时查看分析状态、处理过程和最终图表结果。",
            "图5 前端步骤4 执行与结果展示界面",
            "图4_前端步骤4_结果展示界面.png",
            6.9,
        ),
        (
            "步骤五：后端算法沿用原有逻辑，完成模态识别、滤波处理和对应算法分析，同时将运行过程中的终端输出实时回传到前端界面。",
            "",
            "",
            0.0,
        ),
        (
            "步骤六：分析完成后，前端结果页展示系统终端运行日志以及生成的结果图像，用户可以在同一界面中查看分析过程与最终图表。",
            "",
            "",
            0.0,
        ),
    ]
    for text, caption, filename, width in step_blocks:
        b.paragraph(text, first_line=0, align="justify")
        if filename:
            b.image(IMG_DIR / filename, width_inches=width)
            b.paragraph(caption, align="center", size_half_points=22, space_after=180)

    b.paragraph("三、软件优势介绍", size_half_points=28, bold=True, space_before=220, space_after=180)
    b.paragraph(
        "用于多模态生理信号的分析系统在保留原有分析框架的基础上，新增了面向用户的可视化前端，使原本偏命令行的分析流程被整理为清晰的分步骤操作流程，降低了使用门槛。系统支持脑电、心电、肌电三类模态，并能根据用户所选模态自动列出默认分析功能，减少人工判断成本。系统支持 CSV 文件拖拽上传，导入方式直观，适合实验环境和教学环境快速使用。系统前后端分层明确，前端负责交互与结果呈现，后端继续复用原有成熟算法模块，既保证了功能稳定性，也便于后续扩展新的界面和算法。系统还能在同一界面中同步展示终端日志和图像结果，使用户能够同时看到分析过程与分析结果，提升了软件的可理解性和可用性。",
        first_line=480,
        align="justify",
    )

    docx_path = OUT_DIR / f"{SOFTWARE_NAME}_软件说明书.docx"
    b.save(docx_path)


def build_code_doc():
    b = DocxBuilder()
    b.paragraph(SOFTWARE_NAME, size_half_points=34, bold=True, align="center", space_before=600, space_after=240)
    b.paragraph("源代码汇编文档", size_half_points=30, bold=True, align="center", space_after=360)
    b.paragraph("以下内容根据当前项目源码自动整理生成，保留主要程序文件及测试文件。", size_half_points=24, first_line=480, align="justify")
    b.page_break()

    file_list = [
        ROOT / "main.py",
        ROOT / "nm_config.py",
        ROOT / "pyproject.toml",
        *sorted((ROOT / "utils").glob("*.py")),
        *sorted((ROOT / "tests").glob("*.py")),
    ]
    for idx, path in enumerate(file_list, start=1):
        b.paragraph(f"{idx}. {path.relative_to(ROOT)}", size_half_points=24, bold=True, space_before=180, space_after=80)
        b.code_block(path.read_text(encoding="utf-8"))

    docx_path = OUT_DIR / f"{SOFTWARE_NAME}_源代码汇编.docx"
    b.save(docx_path)


def main():
    build_manual_doc()
    build_code_doc()


if __name__ == "__main__":
    main()
