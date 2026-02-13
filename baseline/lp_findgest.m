function mOut = lp_findgest(lpState, action, varargin)
%LP_FINDGEST  - MVIEW labelling procedure delimiting gestural extents
%
% This procedure identifies the following gestural landmarks on the signal(s) displayed within
% the ctl-clicked panel using velocity criteria computed with central differencing.  Velocity 
% is either tangential (if multiple components are displayed) or absolute magnitude (if one
% component displayed).
%
%	MAXC  - closest vel minimum to clicked offset (assumed to be maximum constriction)
%	PVEL  - offset of the peak velocity preceding MAXC
%	PVEL2 - offset of the peak velocity following MAXC
%	GONS  - gestural onset (THRESH% of the range between the minimum preceding PVEL and PVEL)
%	NONS  - nucleus onset (THRESH% of the range between PVEL and MAXC)
%	NOFFS - nucleus offset (THRESH% of the range between MAXC and following peak velocity PVEL2)
%	GOFFS - gestural offset (THRESH% of the range between PVEL2 and following minimum)
%
% Once created labels can be moved by clicking and dragging.  Label EXPORT appends these seven 
% offset values (in msecs), plus position (in mm), magnitude velocity (cm/sec) for each, as well
% as PD (peak displacement, Euclidean distance between GONS and MAXC in mm) and PD2 (GOFFS:MAXC).
% Double-click on a label to edit; delete will eliminate all labels associated with that gesture.
% Add comments to a label group by entering text into the NOTE field of any of its labels.
% Use shift-click to set a reference (non-gesture) label.  Reference labels may be saved but
% are ignored on export.
%
% Behavior is determined by these parameters set in the configuration dialog:
%	PLOT     - enable this to display a separate diagnostic plot of the labelled gesture
%	DELBOX   - if disabled gestural boxes are deleted along with their labels
%	THRGONS  - gestural onset threshold (percentage of min preceding GONS:PVEL range)
%	THRNONS  - nucleus onset threshold (percentage of PVEL:MAXC range)
%	THRNOFF  - nucleus offset threshold (percentage of MAXC:PVEL2 range)
%	THRGOFF  - gestural offset threshold (percentage of PVEL2:min following GOFFS range)
%	ONSTHR   - onset peak vel must exceed this percentage of selection max velocity:  {.2}
%	OFFSTHR  - offset peak vel must exceed this percentage of selection max velocity:  {.15}
%
% The currently displayed selection is used to constrain both MAXC detection and gestural amplitude
% validation (using ONSTHR and OFFSTHR); all fitted labels are also constrained to this interval
%
% see also DELIMITGEST which does the work

% mkt 05/06
% mkt 05/09 mods for constrained selection and cetera
% mkt 01/17 formatting
% mkt 02/23 export PD

idString = 'LP_FINDGEST';
screen = '<SCREEN>';

%	branch by action

switch action,
		
%-----------------------------------------------------------------------------
% CONFIG:  handle configuration
%
% 	returns MOUT = new internal state

	case 'CONFIG',
		mOut = DoConfig(lpState, idString, screen);
		return;
		
		
%-----------------------------------------------------------------------------
% DOWN:  handle mouseDown
%
%	arg(1)	- cursor loc (msecs)

	case 'DOWN',
		mOut = [];
		
% shift-click:  set interactive ref label at specified offset
		if strcmpi(get(gcbf,'selectionType'),'extend'),
			mview('MAKELBL',[],1);
			return;
		end;
		
% set gesture label
		state = get(gcbf, 'userData');		% retrieve mview state
		if isempty(state.CLICKINFO), return; end;		% need clicked trajectory

% get clicked trajectory
		ti = state.CLICKINFO(1);
		pos = state.DATA(ti).SIGNAL;
		sr = state.DATA(ti).SRATE;
		if sr > 5000, return; end;			% ignore non-mvt signals
		if length(state.CLICKINFO) < 4,
			comp = 1;						% monodimensional
			dim = 1;
		else,
			comp = state.CLICKINFO(4:6);	% active components
			dim = state.IS3D + 2;			% number of dimensions
		end;
		s = pos(:,find(comp));
		k = sum(comp);
		if k < dim,
			tName = state.DATA(ti).NAME;
			xyz = 'XYZ';
			tName = [tName,'_',xyz(find(comp))];
		else,
			tName = state.DATA(ti).NAME;
		end;
		offs = floor(sr*varargin{1}/1000) + 1;
		ht = floor(sr*[state.HEAD,state.TAIL]/1000) + 1;
		ps = 'FT';
		[g,v] = DelimitGest(s, offs, ht, 'THRGONS',lpState.THRGONS, 'THRNONS',lpState.THRNONS, ...
					'THRNOFF',lpState.THRNOFF, 'THRGOFF',lpState.THRGOFF, ...
					'ONSTHR',lpState.ONSTHR, 'OFFSTHR',lpState.OFFSTHR, 'FCLP',lpState.FCLP, ...
					'PLOT',ps(lpState.PLOT+1), 'USEFV',ps(lpState.FILTER+1), 'TITLE',tName);
		if isempty(g), beep; return; end;	% on error/no gesture found
		if lpState.PLOT, fprintf('%s:  ', tName); g, end;	% echo gestural values
		names = fieldnames(g);
		g.TPI = state.CLICKINFO(2);			% index of clicked panel
		g.NOW = now;						% label grouping
		g.COMP = find(comp);		
		for k = 1 : 7,						% don't label magnitudes
			label = struct('NAME', names{k}, ...
							'OFFSET', 1000*(g.(names{k})-1)/sr, ...
							'VALUE', [], ...
							'HOOK', tName);
			switch names{k},
				case 'PVEL', label.VALUE = {idString , g.NOW , g.PV , pos , v , sr , g.COMP};
				case 'MAXC', label.VALUE = {idString , g.NOW , g.PD , g};
				otherwise,   label.VALUE = {idString , g.NOW};
			end;
			mview('MAKELBL', label, -1);
		end;
		

%-----------------------------------------------------------------------------
% EXPORT:  label export handler
%
%	arg(1)	- labels
%	arg(2)	- source variable name
%
% offsets and magnitudes from each gestural label group appended as 
% a tab-delimited line in specified text file

	case 'EXPORT',
		labels = varargin{1};
		vName = varargin{2};
		if isempty(labels), return; end;
		state = get(gcbf, 'userData');		% retrieve mview state
		
% parse label data into groups
		gl = {};		% gesture list
		gt = [];		% gesture timestamps
		s = {};			% signals
		v = {};			% velocities
		sr = [];		% sampling rates
		pd = [];		% peak displacements
		tName = {};		% trajectory names
		lidx = [];		% label:gesture mapping
		li = 1;			% label index
		while li <= length(labels),
			label = labels(li);

% ignore labels not created by lp_findgest
			if isempty(label.VALUE) || ~(iscell(label.VALUE) && strcmp(label.VALUE{1}, idString)),		
				li = li + 1;
				continue;
			end;
			
% labels grouped by timestamp
			gi = 1;			% gesture index
			while (gi <= length(gt)),
				if gt(gi) == label.VALUE{2}, break; end;	% matching timestamp
				gi = gi + 1;
			end;
			lidx(li) = gi;
			gt(gi) = label.VALUE{2};					% update timestamp
			if gi > length(gl),
				g = [];
			else,
				g = gl{gi};								% current gesture
			end;

% append this label to group
			gl{gi} = setfield(g, label.NAME, label.OFFSET);
			switch label.NAME,
				case 'PVEL',							% extra info attached to PVEL labels
					tName{gi} = label.HOOK;					% trajectory name
					s{gi} = label.VALUE{4};					% source signal
					v{gi} = label.VALUE{5};					% velocity signal
					sr(gi) = label.VALUE{6};				% sampling rate
					comp{gi} = label.VALUE{7};				% components this gesture defined upon
				case 'MAXC',							% extra info attached to MAXC labels
					dg = label.VALUE{4};					% copy of DelimitGest results
					pd(gi,:) = [dg.PD , dg.PD2];			% peak displacements
				otherwise,
			end;
			li = li + 1;
			
		end;
		if isempty(tName) || isempty(tName{gi}), error('missing required PVEL component'); end;

% validate gestural groups
		k = zeros(1,length(gl));
		for gi = 1 : length(gl),
			gl{gi} = ValidateGest(gl{gi}, tName{gi});
			if isempty(gl{gi}), 
				k(gi) = 1; 				% invalid gesture
			else,						% accumulate comments
				[tName{gi},comment] = ParseComments({labels(find(lidx==gi)).HOOK});
				gl{gi}.TNAME = tName{gi};
				gl{gi}.COMMENT = comment;
			end;
		end;
		gl(find(k)) = [];
		
% open the file
		fName = lpState.FNAME;
		isNew = ~exist(fName,'file');
		if strcmp(fName,screen),
			fid = 1;
		else,
			fid = fopen(fName, 'at');
			if fid == -1,
				error(sprintf('error attempting to open %s', fName));
			end;
		end;
		
% write headers if necessary
		if isNew,
			fprintf(fid, 'SOURCE\tTRAJ\tCOMMENT\tGONS (ms)\tPVEL (ms)\tNONS (ms)\tMAXC (ms)\tNOFFS (ms)\tPVEL2 (ms)\tGOFFS (ms)\t');
			fprintf(fid, 'GONS (X mm)\tPVEL (X mm)\tNONS (X mm)\tMAXC (X mm)\tNOFFS (X mm)\tPVEL2 (X mm)\tGOFFS (X mm)\t');
			fprintf(fid, 'GONS (Y mm)\tPVEL (Y mm)\tNONS (Y mm)\tMAXC (Y mm)\tNOFFS (Y mm)\tPVEL2 (Y mm)\tGOFFS (Y mm)\t');
			if state.IS3D,
				fprintf(fid, 'GONS (Z mm)\tPVEL (Z mm)\tNONS (Z mm)\tMAXC (Z mm)\tNOFFS (Z mm)\tPVEL2 (Z mm)\tGOFFS (Z mm)\t');
			end;
			fprintf(fid, 'GONS (V cm/sec)\tPVEL (V cm/sec)\tNONS (V cm/sec)\tMAXC (V cm/sec)\tNOFFS (V cm/sec)\tPVEL2 (V cm/sec)\tGOFFS (V cm/sec)\tPD (mm)\tPD2 (mm)\n');
		end;
		
% append label data
		fprintf(fid, '%s', vName);			% source name
		for gi = 1 : length(gl),
			g = struct2cell(gl{gi});
			[q(1),q(2),q(3),q(4),q(5),q(6),q(7),TNAME,COMMENT] = deal(g{:});
			k = floor(q*sr(gi)/1000) + 1;		% -> samps
			k(find(isnan(k))) = 1;
			pos = s{gi}(k,:);					% pos (X,Y,Z mm)
			vel = sr(gi) * v{gi}(k) / 10;		% vel (cm/sec)
			fprintf(fid, '\t%s\t%s', TNAME, COMMENT);
			if any(isnan(q)),			% missing labels -- slow way
				for qi = 1 : length(q),			% offsets (ms)
					if isnan(q(qi)), fprintf(fid, '\tX'); else, fprintf(fid, '\t%.1f', q(qi)); end;
				end;
				for qi = 1 : length(q),			% posX (mm)
					if isnan(q(qi)), fprintf(fid, '\tX'); else, fprintf(fid, '\t%.1f', pos(qi,1)); end;
				end;
				for qi = 1 : length(q),			% posY (mm)
					if isnan(q(qi)), fprintf(fid, '\tX'); else, fprintf(fid, '\t%.1f', pos(qi,2)); end;
				end;
				if state.IS3D,
					if any(comp{gi} == 3),
						for qi = 1 : length(q),			% posZ (mm)
							if isnan(q(qi)), fprintf(fid, '\tX'); else, fprintf(fid, '\t%.1f', pos(qi,3)); end;
						end;
					else,
						fprintf(fid, '\tX\tX\tX\tX\tX\tX\tX');
					end;
				end;
				for qi = 1 : length(q),			% vel (cm/sec)
					if isnan(q(qi)), fprintf(fid, '\tX'); else, fprintf(fid, '\t%.1f', vel(qi)); end;
				end;
			else,						% all labels present -- expedite
				fprintf(fid, '\t%.1f', q);			% offsets (ms)
				if any(comp{gi} == 1),
					fprintf(fid, '\t%.1f', pos(:,1));	% posX (mm)
				else,
					fprintf(fid, '\tX\tX\tX\tX\tX\tX\tX');
				end;
				if any(comp{gi} == 2),
					fprintf(fid, '\t%.1f', pos(:,2));	% posY (mm)
				else,
					fprintf(fid, '\tX\tX\tX\tX\tX\tX\tX');
				end;
				if state.IS3D,
					if any(comp{gi} == 3),
						fprintf(fid, '\t%.1f', pos(:,3));	% posZ (mm)
					else,
						fprintf(fid, '\tX\tX\tX\tX\tX\tX\tX');
					end;
				end;
				fprintf(fid, '\t%.3f', vel);	% vel (cm/sec)
			end;
			fprintf(fid,'\t%.3f\t%.3f', pd(gi,:));		% peak displacement (GONS:MAXC, MAXC:GOFFS; mm)
			fprintf(fid, '\n');
		end;
		
% clean up
		if fid > 1, 
			fclose(fid);
			fprintf('\nLabels from %s appended to %s\n', vName, lpState.FNAME);
		end;
		mOut = [];
		
		
%-----------------------------------------------------------------------------
% PLOT:  plot label into the current axes
%
%	arg(1)	- label to plot
%	arg(2)	- yLim of current axis
%	arg(3)  - figure handle

	case 'PLOT',				% default handler
		label = mview('LPLOT', varargin{:});

% plot gestural box		
		if strcmp(label.NAME,'MAXC'),
			g = label.VALUE{4}; gc = struct2cell(g);
			[GONS,PVEL,NONS,MAXC,NOFFS,PVEL2,GOFFS] = deal(gc{1:7});
			TPI0 = g.TPI; PD = g.PD;
			fh = varargin{3};
			state = get(fh, 'userData');
			q = mview('CALLFCN','ParseTempMap',state.TEMPMAP,label.HOOK,[]);
			TPI = q{1};
			if TPI == 0, TPI = TPI0; end;
			if TPI > 0,
				set(state.SPATIALH,'visible','off');
				ah = gca;
				axes(state.TPANELS(TPI).AXIS);
				col = get(state.TPANELS(TPI).LH(1),'color');
				ylim = get(gca,'ylim');
				xx = [GONS GONS GOFFS GOFFS GONS];
				yy = [-1 1 1 -1 -1]*.5*PD + ylim(1) + diff(ylim)/2;
				h(1) = line(xx,yy,'color',col,'lineWidth',2,'tag','GESTBOX');
				xx = [NONS NONS NOFFS NOFFS NONS];
				h(2) = patch(xx,yy,col,'tag','GESTBOX');
				if verLessThan('matlab','8.4.0'), set(h(2), 'eraseMode','xor'); end
				h(3) = line([MAXC,MAXC],yy(1:2),'color','w','linestyle','--','tag','GESTBOX');
				axes(ah);
				set(state.SPATIALH,'visible','on');
				label.HANDS = [label.HANDS , h];
			end;
		end;
		
% allow motion
		set(label.HANDS(1), 'buttonDownFcn', 'mview(''LMOVE'',''DOWN'');');
		mOut = label;
		

%-----------------------------------------------------------------------------
% error

	otherwise,
		error(['LP_FINDGEST:  unrecognized action (', action, ')']);
	
end;


%=============================================================================
% DEFCFG  - set default configuration
%
%	returns default values for lpState

function lpState = DefCfg(idString, screen)

lpState = struct('SOURCE', idString, ...
					'FNAME', screen, ...
					'THRGONS', .2, ...
					'THRNONS', .2, ...
					'THRNOFF', .2, ...
					'THRGOFF', .2, ...
					'ONSTHR', .2, ...
					'OFFSTHR', .15, ...
					'FCLP', .2, ...
					'FILTER', 0, ...
					'PLOT', 0, ...
					'DELBOX', 1);
				

%=============================================================================
% DOCONFIG  - config handler
%
%   returns non-empty lpState on OK, [] on cancel
%

function lpState = DoConfig(lpState, idString, screen)

width = 320; height = 500;
if ispc, height = height-30; end;
figPos = CenteredDialog(gcf, width, height);

% 	initialize if necessary

if isempty(lpState) | ~isfield(lpState,'SOURCE') | ~strcmp(lpState.SOURCE, idString),
	lpState = DefCfg(idString, screen);
end;

cfg = dialog('Name', idString, ...
	'Tag', 'MVIEW', ...
	'menubar', 'none', ...
	'Position', figPos, ...
	'KeyPressFcn', 'set(gcbf,''UserData'',1);uiresume', ...
	'UserData', 0);

% about
blurb = ['This procedure uses the tangential velocity of the displayed signal components within the clicked panel to ', ...
		 'create 7 labels relative to the ctl-clicked location:  gestural on/offset, nucleus on/offset, ', ...
		 'max constriction, and peak velocities (shift-click sets arbitrary label)'];

uicontrol(cfg, ...
	'Style', 'frame', ...
	'Position', [10 height-100 width-20 90]);
uicontrol(cfg, ...
	'Style', 'text', ...
	'HorizontalAlignment', 'left', ...
	'String', blurb, ...
	'Position', [13 height-97 width-26 84]);

% label filename
w = 18;
h = 23.5;
if ispc, w = w + 18; h = h + 1.5; end;
uicontrol(cfg, ...
	'Style','text', ...
	'HorizontalAlignment', 'right', ...
	'String','Export filename:', ...
	'Units', 'characters', ...
	'Position', [2 h+.2 w-3 1.5]);
fn = uicontrol(cfg, ...
	'Style', 'edit', ...
	'HorizontalAlignment', 'left', ...
	'String', sprintf(' %s',lpState.FNAME), ...
	'Units', 'characters', ...
	'Position', [w h+.2 22 1.8]);

% thresholds
w = 30;
if ispc, w = w + 18; end;
h = h-2;
uicontrol(cfg, ...
	'Style','text', ...
	'HorizontalAlignment', 'right', ...
	'String','Gestural Onset Thresh (%):', ...
	'Units', 'characters', ...
	'Position', [1 h w 1.5]);
gonsH = uicontrol(cfg, ...
	'Style', 'edit', ...
	'HorizontalAlignment', 'left', ...
	'String', sprintf(' %.2f',lpState.THRGONS), ...
	'Units', 'characters', ...
	'Position', [w+2 h+.2 8 1.8]);
h = h-2;
uicontrol(cfg, ...
	'Style','text', ...
	'HorizontalAlignment', 'right', ...
	'String','Nucleus Onset Thresh (%):', ...
	'Units', 'characters', ...
	'Position', [1 h w 1.5]);
nonsH = uicontrol(cfg, ...
	'Style', 'edit', ...
	'HorizontalAlignment', 'left', ...
	'String', sprintf(' %.2f',lpState.THRNONS), ...
	'Units', 'characters', ...
	'Position', [w+2 h+.2 8 1.8]);
h = h-2;
uicontrol(cfg, ...
	'Style','text', ...
	'HorizontalAlignment', 'right', ...
	'String','Nucleus Offset Thresh (%):', ...
	'Units', 'characters', ...
	'Position', [1 h w 1.5]);
noffsH = uicontrol(cfg, ...
	'Style', 'edit', ...
	'HorizontalAlignment', 'left', ...
	'String', sprintf(' %.2f',lpState.THRNOFF), ...
	'Units', 'characters', ...
	'Position', [w+2 h+.2 8 1.8]);
h = h-2;
uicontrol(cfg, ...
	'Style','text', ...
	'HorizontalAlignment', 'right', ...
	'String','Gestural Offset Thresh (%):', ...
	'Units', 'characters', ...
	'Position', [1 h w 1.5]);
goffsH = uicontrol(cfg, ...
	'Style', 'edit', ...
	'HorizontalAlignment', 'left', ...
	'String', sprintf(' %.2f',lpState.THRGOFF), ...
	'Units', 'characters', ...
	'Position', [w+2 h+.2 8 1.8]);
h = h-2;
uicontrol(cfg, ...
	'Style','text', ...
	'HorizontalAlignment', 'right', ...
	'String','Onset PV / sel max vel Thresh (%):', ...
	'Units', 'characters', ...
	'Position', [1 h w 1.5]);
onsH = uicontrol(cfg, ...
	'Style', 'edit', ...
	'HorizontalAlignment', 'left', ...
	'String', sprintf(' %.2f',lpState.ONSTHR), ...
	'Units', 'characters', ...
	'Position', [w+2 h+.2 8 1.8]);
h = h-2;
uicontrol(cfg, ...
	'Style','text', ...
	'HorizontalAlignment', 'right', ...
	'String','Offset PV / sel max vel Thresh (%):', ...
	'Units', 'characters', ...
	'Position', [1 h w 1.5]);
offsH = uicontrol(cfg, ...
	'Style', 'edit', ...
	'HorizontalAlignment', 'left', ...
	'String', sprintf(' %.2f',lpState.OFFSTHR), ...
	'Units', 'characters', ...
	'Position', [w+2 h+.2 8 1.8]);

h = h-2;
uicontrol(cfg, ...
	'Style','text', ...
	'HorizontalAlignment', 'right', ...
	'String','Filtering FcLP (% of Nyquist):', ...
	'Units', 'characters', ...
	'Position', [1 h w 1.5]);
fclpH = uicontrol(cfg, ...
	'Style', 'edit', ...
	'HorizontalAlignment', 'left', ...
	'String', sprintf(' %.2f',lpState.FCLP), ...
	'Units', 'characters', ...
	'Position', [w+2 h+.2 8 1.8]);

% use filtered signal
w = 15;
if ispc, w = w + 5; end
h = h-2;
filtH = uicontrol(cfg, ...
	'Style', 'checkBox', ...
	'String', 'use filtered', ...
	'Units', 'characters', ...
	'Value', lpState.FILTER, ...
	'Position', [w h 20 1.5]);
	
% delete boxes
h = h - 2;
delH = uicontrol(cfg, ...
	'Style', 'checkBox', ...
	'String', 'Delete Boxes', ...
	'Units', 'characters', ...
	'Value', lpState.DELBOX, ...
	'Position', [w h 20 1.5]);
	
% plot
h = h - 2;
plotH = uicontrol(cfg, ...
	'Style', 'checkBox', ...
	'String', 'Diagnostic Plot', ...
	'Units', 'characters', ...
	'Value', lpState.PLOT, ...
	'Position', [w h 20 1.5]);
	

% OK, cancel buttons
uicontrol(cfg, ...		% buttons
	'Position',[width/2-70 15 60 25], ...
	'String','OK', ...
	'Callback','set(gcbf,''UserData'',1);uiresume');
uicontrol(cfg, ...
	'Position',[width/2+10 15 60 25], ...
	'String','Cancel', ...
	'Callback','uiresume');

% wait for input
while 1,
	uiwait(cfg);
	if ~ishandle(cfg), lpState = []; return; end;
	if get(cfg, 'UserData'),
		bad = 0;
		h = [gonsH,nonsH,noffsH,goffsH,onsH,offsH,fclpH];
		for k = 1 : length(h),
			t(k) = str2num(get(h(k), 'string'));
			if isempty(t(k)) | t(k)<0 | t(k)>1,
				set(h(k),'string',' 0.2');
				bad = 1;
				set(cfg, 'userData', 0);
				break;
			end;
		end;
		if bad, continue; end;
		fName = strtok(get(fn, 'string'));
		if isempty(fName) || strcmp(fName,screen), 
			fName = screen;
		else,
			[p,f,e] = fileparts(fName);
			if isempty(e), e = '.lab'; end;
			fName = fullfile(p,[f,e]);
		end;
		lpState.FNAME = fName;
		lpState.THRGONS = t(1);
		lpState.THRNONS = t(2);
		lpState.THRNOFF = t(3);
		lpState.THRGOFF = t(4);
		lpState.ONSTHR  = t(5);
		lpState.OFFSTHR = t(6);
		lpState.FCLP = t(7);
		lpState.FILTER = get(filtH, 'value');
		lpState.PLOT = get(plotH, 'value');
		lpState.DELBOX = get(delH, 'value');
	else,
		lpState = [];
	end;
	break;
end;
delete(cfg);

%=============================================================================
% PARSECOMMENTS  - return gesture trajectory name and comments
%
% gesture group labels use the HOOK field to record the clicked trajectory by
% default; however, users may potentially alter a label's HOOK field through
% editing -- this procedure assumes that the largest number of equivalent
% HOOK fields encodes the trajectory, and all others are concatenated to
% form the comment

function [tName,comment] = ParseComments(hooks)

sh = unique(hooks);
count = zeros(1,length(sh));
for k = 1 : length(sh),
	count(k) = length(strmatch(sh{k},hooks,'exact'));
end;
[v,k] = sort(count);
sh = sh(k);
tName = sh{end};
comment = '';
for k = 1 : length(sh)-1,
	comment = [comment , sh{k} , ' '];
end;
if ~isempty(comment), comment(end) = []; end;


%=============================================================================
% VALIDATEGEST  - verify that required labels present for gestural group
%					based on timestamp; insert placeholders for missing labels

function g = ValidateGest(g, tName)

if isempty(g), return; end;

names = {'GONS','PVEL','NONS','MAXC','NOFFS','PVEL2','GOFFS'};

% verify all labels available this gesture
gNames = fieldnames(g);
if length(gNames) ~= length(names),
	for gi = 1 : length(gNames),
		if isempty(strmatch(gNames{gi}, names)),
			fprintf('extraneous gestural label:  %s (skipped)\n', gNames{gi});
			g = [];
			return;
		end;
	end;
end;
gg = g;
g = struct('GONS',NaN,'PVEL',NaN,'NONS',NaN,'MAXC',NaN,'NOFFS',NaN,'PVEL2',NaN,'GOFFS',NaN,'TNAME',tName,'COMMENT','');
for ni = 1 : length(names),
	if isempty(strmatch(names{ni},gNames,'exact')),
		switch names{ni},
			case {'PVEL','MAXC'},		% these are required
				fprintf('incomplete gestural label group:  missing %s (skipped)\n', names{ni});
				g = [];
				return;
			otherwise,					% any others may be missing; use NaN placeholder here
		end;
	else,
		g = setfield(g,names{ni},getfield(gg,names{ni}));
	end;
end;
