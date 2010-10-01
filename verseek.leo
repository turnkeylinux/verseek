<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet ekr_test?>
<leo_file>
<leo_header file_format="2" tnodes="0" max_tnode_index="51" clone_windows="0"/>
<globals body_outline_ratio="0.5">
	<global_window_position top="0" left="449" height="933" width="800"/>
	<global_log_window_position top="0" left="0" height="0" width="0"/>
</globals>
<preferences/>
<find_panel_settings/>
<vnodes>
<v t="zaril.20101001195902" a="E"><vh>Project</vh>
<v t="zaril.20101001201018" a="E"><vh>development log</vh>
<v t="zaril.20101001195902.1" a="E"><vh>design</vh>
<v t="zaril.20101001195902.2" a="E"><vh>brainstorming</vh></v>
<v t="zaril.20101001195902.5"><vh>cli syntax and logic</vh></v>
</v>
<v t="zaril.20101001201018.3" a="E"><vh>implementation</vh>
<v t="zaril.20101001204645"><vh>cli stubs</vh></v>
<v t="zaril.20101001204243" a="E"><vh>setup tests</vh></v>
<v t="zaril.20101001204304" a="ETV"><vh>support latest version in all types</vh></v>
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
<t tx="zaril.20101001195902.5">operations
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
<t tx="zaril.20101001204243">+ regular
+ tagged
+ multi-git
+ multi-sumo

REMINDERS: 
    dpkg-parsechangelog
        parses changelog

    dch --create
        creates a new changelog according to template

</t>
<t tx="zaril.20101001204304">regular
tagged
multi-git
multi-sumo</t>
<t tx="zaril.20101001204645"></t>
</tnodes>
</leo_file>
