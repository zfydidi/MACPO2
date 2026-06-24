%% Last Modification 2024-12-26
%%%%%%%%%%%%%%%%%%%%%
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{gdu}[2024/12/26 document class]

\LoadClass[10.5pt,oneside,a4paper]{ctexart}
\RequirePackage{mwe}
\RequirePackage{calc}
\RequirePackage{fancyhdr}
\RequirePackage{lastpage}
\RequirePackage{graphicx,epstopdf}
\graphicspath{{./figure/}{./Figures/}{./image/}{./images/}}
\RequirePackage{lastpage}
\RequirePackage{ifthen}
\RequirePackage{float}
\RequirePackage{amsmath}
\RequirePackage{amssymb}
\RequirePackage{mathrsfs,amsfonts}
\RequirePackage{refcount}  
\RequirePackage{changepage}
\RequirePackage{upgreek} 
\RequirePackage{array}
\RequirePackage{tabularx,longtable,makecell}
\RequirePackage{hhline}
\newcommand{\PreserveBackslash}[1]{\let\temp=\\#1\let\\=\temp}
\newcolumntype{C}[1]{>{\PreserveBackslash\centering}p{#1}}
\newcolumntype{R}[1]{>{\PreserveBackslash\raggedleft}p{#1}}
\newcolumntype{L}[1]{>{\PreserveBackslash\raggedright}p{#1}}

\RequirePackage{tikz}
\RequirePackage{eso-pic}
\RequirePackage{booktabs,multirow,float}
\RequirePackage{amsmath}
\RequirePackage{mathtools}
\RequirePackage{amsfonts}
\RequirePackage{amsthm}
\RequirePackage{amssymb}
\RequirePackage{pbox}
\RequirePackage{fontenc}
% \RequirePackage{fontspec}
\setmainfont{Times New Roman}
% \setCJKmainfont[AutoFakeBold,AutoFakeSlant,BoldFont={SimHei},ItalicFont={KaiTi}]{SimSun} 
% \newfontfamily\kaiti{KaiTi}
\usetikzlibrary{calc}
\usetikzlibrary{decorations.pathmorphing}

\RequirePackage{xcolor,colortbl}

\newtoks\CTitle                %学位论文题目
\newtoks\StudentNumber  %学号
\newtoks\Cmajor               %学科专业中文名 or 所学专业或学科或领域
\newtoks\JointDate            %入学年月
\newtoks\college               %学院   
\newtoks\Csupervisor       %指导教师姓名

\newtoks\MasterName          %研究生姓名
\newtoks\MasterNumber       %研究生学号
\newtoks\EducationType      %攻读学位类型

% caption settings 
\RequirePackage{caption}
\captionsetup{labelfont = bf}
\RequirePackage[font=small,labelfont={bf}]{caption} 
\captionsetup[table]{position=top, labelsep=space, skip=3pt,aboveskip=6pt, belowskip=-6pt, singlelinecheck=on, justification=justified}
\captionsetup[figure]{position=bottom, labelsep=space, skip=3pt,aboveskip=6pt, belowskip=-6pt, singlelinecheck=on, justification=justified}

%% pagesize
\RequirePackage{geometry}
\geometry{
	left=2cm,  
	right=2cm, 
	top=1.5cm, 
      bottom=1.75cm
}

\RequirePackage[%
      breaklinks,
	unicode,
	linktoc=all,
	bookmarksnumbered=true,
	bookmarksopen=true,
	colorlinks,
	linkcolor=winered,
	citecolor=winered,
	urlcolor  = black,
	pdfstartview=FitH,
	backref=true,
	pdfborder={0 0 0}]{hyperref}

\RequirePackage{titlesec}
\RequirePackage{tocloft}

\renewcommand\thesection{\zhnum[style=Traditional]{section}}
\titleformat{\section}[hang]{\bfseries}{\thesection、}{1pt}{\bfseries\raggedright}
\titlespacing{\section}{12pt}{2\baselineskip}{\baselineskip}

\titleformat{\subsection}[hang]{\bfseries}{\thesubsection.}{1pt}{\bfseries\raggedright}

\endinput


