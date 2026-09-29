{ MakeFabZip.pas

  Runs JLCPCB-PCBWay-Fabrication.OutJob, then zips the Gerber and NC drill files it
  wrote into "<project name>.zip" in "Project Outputs for <project name>".

  An OutJob cannot zip Gerbers itself, so the zipping is handed to Make-FabZip.ps1
  (next to this script). Only files written by this run go into the zip, so a stale
  Gerber from an older layer set cannot reach the fab.

  Run via File > Run Script, pick MakeFabZip.PrjScr > Run. The OutJob must already
  be part of the board project, and that project must be open. }

const
    OUTJOB_NAME   = 'JLCPCB-PCBWay-Fabrication.OutJob';
    OUTPUT_MEDIUM = 'JLCPCB-PCBWay';


{ The board project that owns the OutJob. The focused project is tried first, but
  running a script can leave the script project focused, so every open .PrjPcb is
  checked for the OutJob next to it. }
function BoardProject : IProject;
var
    Workspace : IWorkspace;
    Candidate : IProject;
    i         : Integer;
begin
    Result    := nil;
    Workspace := GetWorkspace;
    Candidate := Workspace.DM_FocusedProject;
    if (Candidate <> nil) and FileExists(ExtractFilePath(Candidate.DM_ProjectFullPath) + OUTJOB_NAME) then
    begin
        Result := Candidate;
        Exit;
    end;
    for i := 0 to Workspace.DM_ProjectCount - 1 do
    begin
        Candidate := Workspace.DM_Projects(i);
        if FileExists(ExtractFilePath(Candidate.DM_ProjectFullPath) + OUTJOB_NAME) then
        begin
            Result := Candidate;
            Exit;
        end;
    end;
end;


procedure Run;
var
    Project  : IProject;
    ProjDir  : String;
    ProjName : String;
    OutDir   : String;
    Since    : String;
begin
    Project := BoardProject;
    if Project = nil then
    begin
        ShowMessage('No open project has ' + OUTJOB_NAME + ' next to it. Open the board project first.');
        Exit;
    end;

    ProjDir  := ExtractFilePath(Project.DM_ProjectFullPath);
    ProjName := ChangeFileExt(ExtractFileName(Project.DM_ProjectFullPath), '');
    OutDir   := ProjDir + 'Project Outputs for ' + ProjName;

    // Taken before generating: Make-FabZip.ps1 only zips files written after this
    Since := FormatDateTime('yyyymmddhhnnss', Now);

    Client.ShowDocument(Client.OpenDocument('OUTPUTJOB', ProjDir + OUTJOB_NAME));
    ResetParameters;
    AddStringParameter('Action', 'Run');
    AddStringParameter('OutputMedium', OUTPUT_MEDIUM);
    AddStringParameter('ObjectKind', 'OutputBatch');
    RunProcess('WorkspaceManager:GenerateReport');

    // No trailing backslash inside the quotes: \" would escape the closing quote
    RunApplication('powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden' +
        ' -File "' + ProjDir + 'tools\Make-FabZip.ps1"' +
        ' -Source "' + OutDir + '\' + OUTPUT_MEDIUM + '"' +
        ' -Zip "' + OutDir + '\' + ProjName + '.zip"' +
        ' -Since ' + Since);
end;
