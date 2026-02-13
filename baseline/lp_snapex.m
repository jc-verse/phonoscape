function mOut = lp_snapex(lpState, action, varargin)
%LP_SNAPEX  - MELBA/MVIEW user labelling procedure (find nearest extremum)
%
% This procedure tracks mouse movement while down and upon release sets a label at
% the nearest extremum (minimum or maximum) relative to the release point.  Its
% behavior is determined by the modification state:  control sets an anonymous 
% label at the nearest minimum to the release offset; shift sets the label at the 
% nearest maximum.
%
% Generates an error if the clicked trajectory has multiple displayed components
%
% This procedure works with either MVIEW or MELBA:  for MVIEW it operates on the
% clicked trajectory; for MELBA on the audio signal

% mkt 10/04

idString = 'LP_SNAPEX';
screen = '<SCREEN>';

%	branch by action (2nd argument)

switch upper(action),
		
%-----------------------------------------------------------------------------
% CONFIG:  handle configuration
%
% 	returns MOUT = new internal state
% 	mOut = [] flags cancelled

	case 'CONFIG',
		mOut = DoConfig(lpState, idString, screen);
		return;
		
		
%-----------------------------------------------------------------------------
% DOWN:  handle mouseDown
%
%	arg(1)	- cursor loc (msecs)
%	arg(2)	- immediate (nonzero if label set by menu command)

	case 'DOWN',
		mOut = [];						% no state update needed
		if nargin>3 & varargin{2},		% menu label creation -- jump to mouseUp handler
			lp_snapex(lpState, 'UP', 1);
			return;
		end;

% init motion handlers		
		set(gcbf,  ...					
			'WindowButtonMotionFcn', sprintf('%s MOVECUR;',lpState.CALLER), ...		% default motion handler
			'WindowButtonUpFcn', sprintf('lp_snapex([],''UP'');',lpState.CALLER), ...	% intercept mouseUp
			'pointer', 'crosshair');							% set crosshair cursor


%-----------------------------------------------------------------------------
% EXPORT:  label export handler
%
%	arg(1)	- state.LABELS
%	arg(2)	- state.NAME

	case 'EXPORT',
		labels = varargin{1};
		if isempty(labels), return; end;
		vName = varargin{2};
		fName = lpState.FNAME;

% open the file
		if strcmp(fName,screen),
			isNew = 1;
			fid = 1;
		else,
			isNew = ~exist(fName,'file');
			fid = fopen(fName, 'at');
			if fid == -1,
				error(sprintf('error attempting to open %s', fName));
			end;
		end;

% write headers if necessary
		if isNew,
			fprintf(fid, 'SOURCE\tTRAJ\tTYPE\tOFFSET\n');
		end;
		
% append label data
		for k = 1 : length(labels),
			if isempty(labels(k).HOOK), ts = '*'; else, ts = labels(k).HOOK; end;
			fprintf(fid, '%s\t%s\t%s\t%.1f\n', vName, labels(k).NAME, ts, labels(k).OFFSET);
		end;

% clean up
		if fid > 1, 
			fclose(fid);
			fprintf('\nLabels from %s appended to %s\n', vName, lpState.FNAME);
		end;
		mOut = [];
		
		
%-----------------------------------------------------------------------------
% IMPORT:  label import handler
%
%	arg(1)	- label filename

	case 'IMPORT',
		fName = varargin{1};
		try,
			fid = fopen(fName,'rt');
			lines = {};
			while 1,
				lx = fgetl(fid);
				if ~ischar(lx), break; end;
				lines{end+1} = lx;
			end;
			fclose(fid);
			lx = regexp(lines{1},'(\w+)','tokens');
			if ~(strcmp(lx{1},'SOURCE') && strcmp(lx{2},'TRAJ')),
				error('unrecognized format');
			end;
			lines(1) = [];
			for k = 1 : length(lines),
				q = regexp(lines{k},'\t','split');
				if isempty(q), continue; end;
				label = struct('NAME',q{2}, 'OFFSET',str2num(q{4}),'VALUE',[],'HOOK',[]);
				mview('MAKELBL',label,-1);
			end;
			fprintf('Labels imported from %s\n', fName);
		catch,
			fprintf('error attempting to read labels from %s\n', fileName);
		end;
		
%-----------------------------------------------------------------------------
% LMOVE:  label movement mouseUp handler

	case 'LMOVE',
		set(gcbf, 'windowButtonMotionFcn', '', 'windowButtonUpFcn', '');
		curPt = get(gca, 'currentPoint');
		state = get(gcbf, 'userData');		% retrieve state
		lbl = state.LABELS(state.LPSTATE.IDX);
		mod = lbl.HOOK;
		if ~isempty(mod) & ischar(mod) & (strcmp(mod,'max') | strcmp(mod,'min')),
			ti = lbl.VALUE(1);
			ci = lbl.VALUE(2);
			if strcmpi(state.LPSTATE.SAVESTATE.CALLER, 'MELBA'),
				s = state.SIGNAL;
				sr = state.SRATE;
			else,
				s = state.DATA(ti).SIGNAL(:,ci);
				sr = state.DATA(ti).SRATE;
			end;
			offset = floor(curPt(1,1)*sr/1000) + 1;
			if state.LPSTATE.SAVESTATE.CONSTRAINT,
				ht = floor([state.HEAD,state.TAIL]*sr/1000) + 1;
				s = s(ht(1):ht(2));
				offset = offset - ht(1) + 1;
			end;
			infl = diff([0 ; diff(s)] > 0);
			if strcmp(mod, 'max'),			% shift:  nearest maximum
				extrema = find(infl < 0);
			else,							%  else:  nearest minimum
				extrema = find(infl > 0);
			end;
			[v,k] = min(abs(extrema - offset));
			offset = 1000 * (extrema(k)-1)/sr;
			if state.LPSTATE.SAVESTATE.CONSTRAINT && ~isempty(offset), offset = offset + state.HEAD; end;
		else,
			offset = curPt(1,1);
		end;
		state.LABELS(state.LPSTATE.IDX).OFFSET = offset;
		set(state.LPSTATE.H, 'xdata', [1 1]*offset);
		if length(state.LABELS(state.LPSTATE.IDX).HANDS)>1,	% move name
			h = state.LABELS(state.LPSTATE.IDX).HANDS(2);
			pos = get(h, 'position');
			pos(1) = offset;
			set(h, 'position', pos);
		end;
		state.LPSTATE = state.LPSTATE.SAVESTATE;
		set(gcbf, 'pointer', 'arrow', 'userData', state);
		set(state.CURSORF, 'string', sprintf('%.1f', state.CURSOR));


%-----------------------------------------------------------------------------
% PLOT:  plot label into the current axes
%
%	arg(1)	- label to plot
%	arg(2)	- yLim of current axis
%
%	return MOUT = updated label

	case 'PLOT',				% default handler
		if isempty(lpState), lpState.CALLER = GetCaller; end;
		label = feval(lpState.CALLER,'LPLOT', varargin{1}, varargin{2}, gcbf);

% set motion handler
		set(label.HANDS(1), 'buttonDownFcn', sprintf('%s(''LMOVE'',''DOWN'',''lp_snapex'');',lpState.CALLER));
		mOut = label;
		

%-----------------------------------------------------------------------------
% UP:  handle mouseUp (on initial label creation)
%
% nargin > 2 on menu label creation

	case 'UP',
		set(gcbf, ...						% clear motion handlers
			'WindowButtonMotionFcn', '', ...
			'WindowButtonUpFcn', '', ...
			'pointer', 'arrow');
		mod = get(gcbf, 'selectionType');
		state = get(gcbf, 'userData');		% retrieve state
		lpState = state.LPSTATE;
		if isfield(state,'CLICKINFO') & ~isempty(state.CLICKINFO),
			clickInfo = state.CLICKINFO;
		else,
			clickInfo = [];
		end;		
		if nargin < 3,
			moveMode = state.MOVEMODE;
			state.MOVEMODE = 'LBL_SILENT';
			set(gcbf, 'userData', state);	% anonymous labels except for menu-created
		end;
		
% get clicked trajectory
		if strcmpi(lpState.CALLER, 'MELBA'),		% melba
			s = state.SIGNAL;
			sr = state.SRATE;
			sn = '';
			ti = 1; ci = 1;
			offset = floor(state.CURSOR*sr/1000) + 1;	% cursor offset (samples)
			if lpState.CONSTRAINT,
				ht = floor([state.HEAD,state.TAIL]*sr/1000) + 1;
				s = s(ht(1):ht(2));
				offset = offset - ht(1) + 1;
			end;
			infl = diff([0 ; diff(s)] > 0);
			if strcmp(mod, 'extend'),		% shift:  nearest maximum
				extrema = find(infl < 0);
				ts = 'max';
			else,							%  else:  nearest minimum
				extrema = find(infl > 0);
				ts = 'min';
			end;
			[v,k] = min(abs(extrema - offset));
			offset = 1000 * (extrema(k)-1)/sr;
			if isempty(offset),
				fprintf('LP_SNAPEX:  %s not found within search range\n',ts);
				return;
			end;
			if lpState.CONSTRAINT, offset = offset + state.HEAD; end;
		else,								% mview
			if isempty(clickInfo),
				clickInfo = [1 1 1];
			end;
			ti = clickInfo(1);
			tpi = clickInfo(2);
			sn = state.TEMPMAP{tpi};
			s = state.DATA(ti).SIGNAL;
			sr = state.DATA(ti).SRATE;
			if length(clickInfo) > 3,		% multidimensional
				comp = clickInfo(4:end);
				switch clickInfo(3),
					case 1, 
						ci = find(comp);
					case 2,
						if sum(comp) == state.DATA(ti).NCOMPS,
							ci = 7;		% velocity magnitude
						else,
							ci = find(comp) + 3;
						end;
					case 3,
						if sum(comp) == state.DATA(ti).NCOMPS,
							ci = 11;	% acceleration magnitude
						else,
							ci = find(comp) + 7;
						end;
				end;
				if length(ci) > 1, 
					fprintf('LP_SNAPEX:  ignoring click in panel %s with multiple displayed trajectories\n',sn);
					return;
				end;
			else,
				if clickInfo(3) >= 6 & sr < 2000,		% velocity
					s(2:end-1) = (s(3:end) - s(1:end-2))./2;
					s(1) = s(2);
					s(end) = s(end-1);
					if clickInfo(3)>6, s = abs(s); end;
				end;
				ci = 1;
			end;
			if sr > 2000,
				offset = [];					% speech; use current cursor offset
				ts = '';
			else,
				s = s(:,ci);					% retain clicked component
				offset = floor(state.CURSOR*sr/1000) + 1;	% cursor offset (samples)
				if lpState.CONSTRAINT,
					ht = floor([state.HEAD,state.TAIL]*sr/1000) + 1;
					s = s(ht(1):ht(2));
					offset = offset - ht(1) + 1;
				end;
				if isnan(s(offset)),			% don't change offset if clicked on NaN sample
					if strcmp(mod, 'extend'),		% shift:  nearest maximum
						ts = 'max';
					else,							%  else:  nearest minimum
						ts = 'min';
					end;
					offset = state.CURSOR;
				else,
					h = find(isnan(s(1:offset)));
					if isempty(h), h = 1; else h = h(end); end;
					t = find(isnan(s(offset:end))) + offset - 1;
					if isempty(t), t = length(s); else, t = t(1); end;
					s = s(h:t);
					if strcmp(mod, 'extend'),		% shift:  nearest maximum
						s(1) = 0; s(end) = 0;
						extrema = find(diff([0 ; diff(s)] > 0) < 0) + h - 1;
						ts = 'max';
					else,							%  else:  nearest minimum
						s(1) = 2*max(s); s(end) = 2*max(s);
						extrema = find(diff([0 ; diff(s)] > 0) > 0) + h - 1;
						ts = 'min';
					end;
					[v,k] = min(abs(extrema - offset));
					offset = 1000 * (extrema(k)-1)/sr;
				end;
				if isempty(offset),
					fprintf('LP_SNAPEX:  %s not found within search range\n',ts);
					return;
				end;
				if lpState.CONSTRAINT, offset = offset + state.HEAD; end;
			end;
		end;

		label = struct('NAME', sn, ...		% clicked signal name
						'OFFSET', offset, ...	% use supplied offset
						'VALUE', [ti ci], ...	% save for movement handler
						'HOOK', ts);			% label type
%						'STYLE', []);			% label plotting style
%		label.STYLE = {'color','g','linewidth',2};
		feval(lpState.CALLER,'MAKELBL', label);		% create the label

		
%-----------------------------------------------------------------------------
% error

	otherwise,
		error(['LP_SNAPEX:  unrecognized action (', varargin{2}, ')']);
	
end;



%=============================================================================
% DEFCFG  - set default configuration
%
%	returns default values for lpState

function lpState = DefCfg(idString, screen)

lpState = struct('SOURCE', idString, ...
					'FNAME', screen, ...
					'CONSTRAINT', 0, ...
					'CALLER', GetCaller);
				

%=============================================================================
% DOCONFIG  - config handler
%
%   returns non-empty lpState on OK, [] on cancel

function lpState = DoConfig(lpState, idString, screen)

width = 350; height = 270;
figPos = CenteredDialog(gcf, width, height);

% initialize if necessary
if isempty(lpState) || ~strcmp(lpState.SOURCE, idString),
	lpState = DefCfg(idString, screen);
end;

cfg = dialog('Name', idString, ...
	'Tag', GetCaller, ...
	'menubar', 'none', ...
	'Position', figPos, ...
	'KeyPressFcn', 'set(gcbf,''UserData'',1);uiresume', ...
	'UserData', 0);

% about
blurb = ['This procedure tracks mouse movement while down and upon release sets a label. ', ...
		'Its behavior is determined by the modification state:  control sets an anonymous ', ...
		'label at the nearest minimum to the release offset; shift sets the label at the ', ...
		'nearest maximum.  This procedure works with either MVIEW or MELBA:  for MVIEW it ', ...
		'operates on the clicked trajectory; for MELBA on the audio signal.'];

uicontrol(cfg, ...
	'Style', 'frame', ...
	'Position', [10 height-130 width-20 120]);
uicontrol(cfg, ...
	'Style', 'text', ...
	'HorizontalAlignment', 'left', ...
	'String', blurb, ...
	'Position', [13 height-125 width-26 110]);

% label filename
h = 6;
uicontrol(cfg, ...
	'Style','text', ...
	'HorizontalAlignment', 'right', ...
	'String','Export filename:', ...
	'Units', 'characters', ...
	'Position', [2 h+.5 18 1.7]);
fn = uicontrol(cfg, ...
	'Style', 'edit', ...
	'HorizontalAlignment', 'left', ...
	'String', sprintf(' %s',lpState.FNAME), ...
	'Units', 'characters', ...
	'Position', [21 h+.7 25 2]);

% search constraint
h = h - 3;
cb = uicontrol(cfg, ...
	'Style', 'checkbox', ...
	'HorizontalAlignment', 'left', ...
	'String', 'Constrain search to current selection', ...
	'Units', 'characters', ...
	'value', lpState.CONSTRAINT, ...
	'Position', [8 h+.7 50 2]);

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
uiwait(cfg);
if ishandle(cfg) && get(cfg, 'UserData'),
	fName = strtok(get(fn, 'string'));
	if isempty(fName) || strcmp(fName,screen), 
		fName = screen;
	else,
		[p,f,e] = fileparts(fName);
		if isempty(e), e = '.lab'; end;
		fName = fullfile(p,[f,e]);
	end;
	lpState.FNAME = fName;
	lpState.CONSTRAINT = get(cb,'value');
else,
	lpState = [];
end;
if ishandle(cfg), delete(cfg); end;


%=============================================================================
% GETCALLER  - get calling procedure name

function caller = GetCaller

stack = dbstack;
[p, caller] = fileparts(stack(end).name);


%=============================================================================
% PARSETEMPMAP  - parse displayed TEMPMAP entry
%
%	usage:  [ti, mod, comp] = ParseTemp(loadedString, sel, comps)
%
% returns trajectory index TI (into DATA), MODification code, active COMPonents

function [ti,mod,comp,allComps] = ParseTempMap(loadedString, sel, comps)

mods = {'SPECT','F0','RMS','ZC','VEL','ABSVEL'};		% supported monodimensional data modifications
allComps = 0;											% true if all components selected

if all(sel > 'Z'), sel = upper(sel); end;

% find prefix movement selector (movement '', velocity 'v', acceleration 'a')
if sel(1) > 'Z',
	if sel(1)=='v', mod = 2; else, mod = 3; end;
	sel = sel(2:end);
else,
	mod = 1;
end;

% find suffix component selector
k = findstr(sel,'_');
if isempty(k),			% movement
	k = find(sel>'Z');
	if isempty(k),
		comp = [];				% all
		allComps = 1;
	else,
		comp = sel(k:end);		% xyz
		sel = sel(1:k-1);
	end;
else,					% mono-dimensional mods
	comp = sel(k+1:end);		% SPECT, F0, RMS, ZC, VEL, ABSVEL
	if isempty(strmatch(comp, mods, 'exact')),
		comp = [];				% traj name with form FOO_BAH
	else,
		sel = sel(1:k-1);
	end;
end;

% find trajectory index
ti = strmatch(upper(sel), loadedString, 'exact');
if isempty(ti),
	ti = 0;						% not found
	return;
end;

% multi-component trajectories
if comps{ti} > 1,
	if isempty(comp),	% unspecified (all)
		comp = [1 1 comps{ti}>2];
	else,				% specified
		comp = [any(comp=='x') , any(comp=='y') , any(comp=='z')];
	end;

% monodimensional data
else,
	if isempty(comp),
		mod = 1;		% data
	else,
		mod = strmatch(comp, mods, 'exact') + 1;
	end;
	comp = [];
end;



