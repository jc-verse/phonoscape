function ApplyPraatLabs(fName, tier, traj, offset)
%APPLYPRAATLABS  - get movement values at Praat labelled offsets
%
%	usage:  ApplyPraatLabs(fName, tier, traj, offset)
%
% use this procedure to apply labels from each <ID>.TextGrid to 
% corresponding T<ID>.mat for all matches within the current
% working directory, writing TRAJectory movement values at the 
% OFFSET percentage into each labelled interval to FNAME.txt
%
% Required Argument:
% FNAME is the name of the tab-delimited output file; assumes ".txt"
% extension if unspecified and data are appended if it exists
%
% TIER is the TextGrid interval tier name
%
% Optional Arguments:
% TRAJ is a cellstr array specifying which movement channels
% to sample (default all); append some combination of x,y,z to 
% select particular component (default all three).  Note that
% channel names should be upper case and component names lower
% case (e.g., 'APEX', 'APEXz')
%
% OFFSET give the percentage of each labelled interval at which to
% sample (default .5)
%
% Examples:
%   Apply labels from tier "voyelle" for all trajectories at 
%   default 50% offset, writing results to "Subj03.txt"
% ApplyPraatLabs('Subj03', 'voyelle')
%
%   Same thing but sampling only horizontal and vertical APEX
%   movement, vertical LL movement at 40% offset
% ApplyPraatLabs('Subj03','voyelle',{'APEXxz','LLz'},.4)
%
% see also mview LPROC LP_GETVALS, DPROC MDP_PRAATLABS

% mkt 08/12

% parse args
if nargin < 2,
	eval('help ApplyPraatLabs');
	return;
end;
if nargin < 3, traj = []; end;
if nargin < 4 || isempty(offset), offset = .5; end;
xyz = 'xyz';
sr = 200;				% assume 200 Hz mvt sampling rate

% get TextGrid list as vector of Carstens indices
idx = str2num(char(gfl('*.TextGrid')))';
if isempty(idx), error('no TextGrid files found'); end;

% get first matching MAT file
fi = 1;
while fi <= length(idx),
	tfn = sprintf('T%03d.mat',idx(fi));
	if exist(tfn,'file'), break; end;
	fi = fi + 1;
end;
if fi > length(idx), error('no MAT files found corresponding to TextGrid labels'); end;

% sanity check on specified traj list
d = LoadMAT(tfn);
availTraj = {d.NAME};		% available trajectory names
if isempty(traj),
	traj = availTraj(find(cell2mat({d.SRATE}) == sr));	% mvt channels only
else,
	for ti = 1 : length(traj),
		[tName,comp] = ParseTraj(traj{ti});
		if isempty(strmatch(tName, availTraj, 'exact')),
			error('trajectory %s not found in movement data', tName);
		end;
	end;
end;

% open output file
[p,f,e] = fileparts(fName);
if isempty(e), fName = fullfile(p,[f,'.txt']); end;
fid = fopen(fName,'at');
if fid == -1, error('unable to open %s for output', fName); end;

% write headers
fprintf(fid,'INDEX\tTIER\tINTERVAL\tOFFSET');
for ti = 1 : length(traj),
	[tName,comp] = ParseTraj(traj{ti});
	for ci = 1 : length(comp),
		fprintf(fid,'\t%s%s', tName, xyz(comp(ci)));
	end;
end;
fprintf(fid,'\n');

% loop over available TextGrid files
for fi = 1 : length(idx),
	tfn = sprintf('T%03d.mat',idx(fi));
	try,
		d = LoadMAT(tfn);
	catch,
		fprintf('no matching %s found for %04d.TextGrid (skipped)\n', tfn, idx(fi));
		continue;
	end;
	[segs,labs] = ReadPraatTier(sprintf('%04d',idx(fi)),tier);
	for li = 1 : length(labs),
		if isempty(labs{li}), continue; end;
		ht = segs(li,:);
		offsMS = (diff(ht)*offset+ht(1))*1000;			% measurement offset (ms)
		offsSAMP = floor(offsMS*sr/1000)+1;				% samps
		fprintf(fid,'%04d\t%s\t%s\t%.1f',idx(fi),tier,labs{li},offsMS);
		for ti = 1 : length(traj),
			[tName,comp] = ParseTraj(traj{ti});
			k = strmatch(tName,availTraj,'exact');
			v = d(k).SIGNAL(offsSAMP,1:3);				% value at offset
			for ci = 1 : length(comp),
				fprintf(fid,'\t%.1f', v(comp(ci)));
			end;			
		end;
		fprintf(fid,'\n');
	end;
	fprintf('.');
end;
fprintf('\n');

% close output file
fclose(fid);
fprintf('wrote %s\n', fName);


%====================================================================================
% PARSETRAJ  - returns trajectory name and components

function [traj,comp] = ParseTraj(traj)

comp = [];

k = findstr(traj,'x'); traj(k) = [];
if ~isempty(k), comp = 1; end;

k = findstr(traj,'y'); traj(k) = [];
if ~isempty(k), comp = [comp , 2]; end;

k = findstr(traj,'z'); traj(k) = [];
if ~isempty(k), comp = [comp , 3]; end;

if isempty(comp), comp = 1:3; end;
