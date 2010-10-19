<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet ekr_test?>
<leo_file>
<leo_header file_format="2" tnodes="0" max_tnode_index="51" clone_windows="0"/>
<globals body_outline_ratio="0.378349410504">
	<global_window_position top="0" left="476" height="933" width="800"/>
	<global_log_window_position top="0" left="0" height="0" width="0"/>
</globals>
<preferences/>
<find_panel_settings/>
<vnodes>
<v t="zaril.20101001195902" a="E"><vh>Project</vh>
<v t="zaril.20101001201018" a="E"><vh>development log</vh>
<v t="zaril.20101001195902.1" a="E"><vh>design</vh>
<v t="zaril.20101001195902.2" a="E"><vh>brainstorming</vh></v>
<v t="zaril.20101001233547"><vh>terminology</vh></v>
<v t="zaril.20101001195902.5"><vh>cli syntax and logic</vh></v>
</v>
<v t="zaril.20101001201018.3" a="E"><vh>implementation</vh>
<v t="zaril.20101001204645"><vh>cli stubs</vh></v>
<v t="zaril.20101001204243" a="E"><vh>setup tests</vh></v>
<v t="zaril.20101001204304" a="E"><vh>support latest version in all types</vh>
<v t="zaril.20101001204304.1"><vh>plain</vh></v>
<v t="zaril.20101001204903"><vh>git single</vh></v>
<v t="zaril.20101002071459"><vh>git</vh></v>
</v>
<v t="zaril.20101005103427"><vh>bug: badly formatted changelog</vh></v>
<v t="zaril.20101007060330" a="E"><vh>support full history</vh>
<v t="zaril.20101019052603" a="ETV"><vh>git-single</vh></v>
</v>
</v>
</v>
<v t="zaril.20101001200109.1"><vh>bugs/wishlist</vh></v>
</v>
</vnodes>
<tnodes>
<t tx="zaril.20101001195902">@nocolor
</t>
<t tx="zaril.20101001195902.1"></t>
<t tx="zaril.20101001195902.2">name
    verseek

    alternatives
        sourceversion    
        dsv
            debiansourceversion
    
source types
    regular directory
        list -&gt; only one version
        seek -&gt; dummy operation

    tagged
        list
            all possible auto-versions

        seek
            saves state
            seeks to version with regular git
            creates changelog

    multi-source git repos

    multi-source Sumo repos
 

cli syntax
    sourceversion-list path
    sourceversion-seek path [ version ]</t>
<t tx="zaril.20101001195902.5">=== ENVIRONMENT

RELEASE (what release to specify in changelog)

=== CLI

operations
    list path -&gt; versions
    seek path [ version ]

verseek -l /path
        lists all versions for the Debian source in that path
            raises error if path is not a valid Debian package

verseek path [ version ]
        if version:
            verify legality of version
            saves current state and seeks to version
                if already in a seek, doesn't save current state
        else:
            restores version prior to seek
                raises error if no seek in progress


</t>
<t tx="zaril.20101001200109.1"></t>
<t tx="zaril.20101001201018"></t>
<t tx="zaril.20101001201018.3">test: unchanged pyproject with trivial changes to wrapper docstring

roadmap/milestones
    cli stubs
    setup tests
    support latest version in all types
    add pool support for subset
    support full history
        support tagged sources
        multi-source git repositories
            create changelog manually
        multi-source sumo repositories
            prerequisite: 
                develop seek capability
                develop commit hooks                

</t>
<t tx="zaril.20101001204243">+ plain
+ git single
+ git
+ sumo

REMINDERS: 
    dpkg-parsechangelog
        parses changelog

    dch --create
        creates a new changelog according to template

</t>
<t tx="zaril.20101001204304">multi-git
multi-sumo</t>
<t tx="zaril.20101001204304.1">list logic
    print the latest version in path

    </t>
<t tx="zaril.20101001204645"></t>
<t tx="zaril.20101001204903">detect logic
    single debian project in Git repositorycd p

calculate version logic
    git-describe commit
    if not, create an untagged autoversion    

list logic
    calculate version (same way scripts/version.sh) does it

seek logic
    verify version
    create changelog


Q: how do we decide what the release for the changelog is?
A: 
    hardwired default
    environment variable
        RELEASE
    cli?
        nah, would just complicate matters

SCRATCH
    git-rev-list

Q: whats the format of the time in the changelog?
A: RFC822
    
	strftime("%a, %d %b %Y %H:%M:%S +0000")
</t>
<t tx="zaril.20101001233547">storage types
    git single
        git repository containing one single package

    git
        git repository containing multiple packages

    plain
        regular directory containing multiple packages

    sumo
        sumo arena containing multiple packages
</t>
<t tx="zaril.20101002071459"></t>
<t tx="zaril.20101005103427">test: dpkg-parsechangelog

parsechangelog/debian: error: badly formatted trailer line, at file debian/changelog line 5
</t>
<t tx="zaril.20101007060330">
git</t>
<t tx="zaril.20101019052603">VERSEEK_HEAD

list logic
    autoversino $(git-rev-list --all)

seek
    if not `git-symbolic-ref VERSEEK_HEAD`:
        git-update-ref VERSEEK_HEAD $(git-symbolic-ref HEAD)

    git-checkout &lt;commit&gt;

seek back
    git-checkout -f $(basename $(git-symbolic-ref VERSEEK_HEAD))
    rm .git/VERSEEK_HEAD
        OR git-symbolic-ref VERSEEK_HEAD ''

seek

Q: can we always rely that head will be pointing to a branch?
A: yes, otherwise we can fail</t>
</tnodes>
</leo_file>
