function mOut = lp_PhaseAng(lpState, action, varargin)
%LP_PHASEANG  - MVIEW user labelling procedure (map offset to phase angle)
%
% This procedure tracks mouse movement while down and upon release sets a label, either at the
% release point (shift-click), or at the nearest velocity minimum relative to the release point
% (ctl-click).  If two labels are set on the same trajectory representing an interval of cyclic 
% behavior (e.g. jaw lowering/raising) then additional labels placed between them, potentially
% on other trajectories, are characterized on export in terms of their phase angle relative to 
% the displacement/velocity cycle determined by the bracketing labels.  Ctl-click and drag on 
% existing labels to snap to a new velocity minimum, or shift-click and drag for hand placement.

% mkt 06/21
% mkt 10/21 include displacement and velocity on export (now to -.tsv)

idString = 'LP_PHASEANG';
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
			lp_PhaseAng(lpState, 'UP', 1);
			return;
		end;

% init motion handlers		
		set(gcbf,  ...					
			'WindowButtonMotionFcn', 'mview MOVECUR;', ...		% default motion handler
			'WindowButtonUpFcn', 'lp_PhaseAng([],''UP'');', ...	% intercept mouseUp
			'pointer', 'crosshair');							% set crosshair cursor


%-----------------------------------------------------------------------------
% EXPORT:  label export handler
%
%	arg(1)	- state.LABELS
%	arg(2)	- state.NAME
%
% DUR is the duration of the interval determined by the current label and 
%	the first label
% ANG is the phase angle measured CW in degrees on the [MVT,VEL] plane defined
%	by the first and last offset labels on a common trajectory (note 0° is North)

	case 'EXPORT',
		labels = varargin{1};
		if isempty(labels), return; end;
		offs = cell2mat({labels.OFFSET});		% ensure temporal sort order
		[~,k] = sort(offs);
		labels = labels(k);
		vName = varargin{2};
		fName = lpState.FNAME;
		state = get(gcbf, 'userData');			% retrieve state
		doPlot = state.LPSTATE.DOPLOT;

% compute phase angles
		gotPA = 0;
		if length(labels) < 3,
			fprintf('at least 3 labels must be defined to obtain phase angles\n');
		elseif ~strcmp(labels(1).NAME, labels(end).NAME),
			fprintf('first and last offset labels must have same trajectory to obtain phase angles\n');
		else,
			[s,ds,sr] = GetSignal(state,labels(1).VALUE);
			if size(s,2) > 1,
				fprintf('phase angle not defined on multidimensional signal\n');
			else,
				gotPA = 1;
				h = floor(labels(1).OFFSET*sr/1000) + 1;	% cursor offset (samples)
				t = floor(labels(end).OFFSET*sr/1000) + 1;
				s = normalize(s(h:t));				% ASSUMPTION:  this represents a cyclic movement (e.g. jaw lowering/raising cycle)
				vo = normalize(ds(h:t),1);			% corresponding velocity (opening phase)
				vc = normalize(ds(h:t),2);			% corresponding velocity (closing phase)
				if doPlot, 
					figure('TAG','MVIEW');
					hh = plot(vo,s,'k-'); hold on; hh(2) = plot(vc,s,'k--');
					n = {'Opening','Closing'};
					axis equal; grid on;
					title(vName,'interpreter','none');
					xlabel(sprintf('Velocity (%s)',labels(1).NAME));
					ylabel(sprintf('Displacement (%s)',labels(1).NAME));
					c = hsv(length(labels)-2);
				end;
				labels(1).DUR = 0;
				labels(1).ANG = 0;
				labels(end).DUR = labels(end).OFFSET - labels(1).OFFSET;
				labels(end).ANG = 360;
				for li = 2 : length(labels)-1,
					labels(li).DUR = labels(li).OFFSET - labels(1).OFFSET;
					k = floor(labels(li).OFFSET*sr/1000) - h + 1;
					if labels(li).DUR / labels(end).DUR <= .5,	% opening phase
						labels(li).ANG = -atan2d(vo(k),s(k));
						x = vo(k);
					else,										% closing phase
						labels(li).ANG = 360 - atan2d(vc(k),s(k));
						x = vc(k);
					end;
					if doPlot,
						hh(li+1) = line([0 x],[0 s(k)],'color',c(li-1,:),'marker','o');
						n{end+1} = sprintf('%s (%.1f°)', labels(li).NAME, labels(li).ANG);
					end;					
				end;
				if doPlot, legend(hh, n{:}); end;
			end;
		end;
		
% find value of JAWz at each label offset
		ji = find(strcmp('JAW',{state.DATA.NAME}));		
		for li = 1 : length(labels),
			if isempty(ji),
				labels(li).HOOK = NaN;		% JAW not available
			else,
				k = floor(labels(li).OFFSET*state.DATA(ji).SRATE/1000) + 1;
				labels(li).HOOK = state.DATA(ji).SIGNAL(k,3);	% JAWz
			end;
		end;	

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
			fprintf(fid, 'SOURCE\tTRAJ\tOFFSET\tDUR\tANGLE\tJAWz\n');
		end;
		
% append label data
		for k = 1 : length(labels),
			if gotPA,
				fprintf(fid, '%s\t%s\t%.1f\t%.1f\t%.1f\t%.1f\n', vName, labels(k).NAME, labels(k).OFFSET, labels(k).DUR, labels(k).ANG, labels(k).HOOK);
			else,
				fprintf(fid, '%s\t%s\t%.1f\tNaN\tNaN\tNaN\n', vName, labels(k).NAME, labels(k).OFFSET);
			end;
		end;

% clean up
		if fid > 1, 
			fclose(fid);
			fprintf('\nLabels from %s appended to %s\n', vName, lpState.FNAME);
		end;
		mOut = [];
		
		
%-----------------------------------------------------------------------------
% IMPORT:  label import handler (unsupported)
%
%	arg(1)	- label filename

	case 'IMPORT',
		fprintf('label import not supported for lp_PhaseAng\n');
				

%-----------------------------------------------------------------------------
% LMOVE:  label movement mouseUp handler

	case 'LMOVE',
		set(gcbf, 'windowButtonMotionFcn', '', 'windowButtonUpFcn', '');
		curPt = get(gca, 'currentPoint');
		mod = get(gcbf, 'selectionType');
		state = get(gcbf, 'userData');			% retrieve state
		lbl = state.LABELS(state.LPSTATE.IDX);
		[s,v,sr] = GetSignal(state,lbl.VALUE);
		if strcmp(mod,'alt') && sr<=2000,		% ctl-click and not speech
			offs = floor(curPt(1,1)*sr/1000) + 1;	% cursor offset (samples)
			h = find(isnan(v(1:offs)));
			if isempty(h), h = 1; else h = h(end); end;
			t = find(isnan(v(offs:end))) + offs - 1;
			if isempty(t), t = length(s); else, t = t(1); end;
			sel = abs(v(h:t));
			sel([1 end]) = 2*max(sel);
			extrema = find(diff([0 ; diff(sel)] > 0) > 0) + h - 1;
			[~,k] = min(abs(extrema - offs));
			offset = 1000 * (extrema(k)-1)/sr;
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
		label = feval(@mview,'LPLOT', varargin{1}, varargin{2}, gcbf);

% set motion handler
		set(label.HANDS(1), 'buttonDownFcn', 'mview(''LMOVE'',''DOWN'',''lp_PhaseAng'');');
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

		if isempty(clickInfo), clickInfo = [1 1 1]; end;
		[s,v,sr] = GetSignal(state, clickInfo);		% get clicked trajectory
		sn = state.TEMPMAP{clickInfo(2)};			% traj name
		
		if sr > 2000,
			offset = [];					% speech; use current cursor offset
		else,
			offs = floor(state.CURSOR*sr/1000) + 1;	% cursor offset (samples)
			if strcmp(mod,'alt') && ~isnan(v(offs)),	% ctl click: find nearest velocity minimum
				h = find(isnan(v(1:offs)));
				if isempty(h), h = 1; else h = h(end); end;
				t = find(isnan(v(offs:end))) + offs - 1;
				if isempty(t), t = length(s); else, t = t(1); end;
				sel = abs(v(h:t));
				sel([1 end]) = 2*max(sel);
				extrema = find(diff([0 ; diff(sel)] > 0) > 0) + h - 1;
				[~,k] = min(abs(extrema - offs));
				offset = 1000 * (extrema(k)-1)/sr;
			else,									% shift click or NaN
				offset = [];							% use current cursor location
			end;
		end;

		label = struct('NAME', sn, ...		% clicked signal name
						'OFFSET', offset, ...	% use supplied offset
						'VALUE', clickInfo, ...	% save for movement handler
						'HOOK', '');			% label type
		mview('MAKELBL', label);			% create the label

		
%-----------------------------------------------------------------------------
% error

	otherwise,
		error(['LP_PHASEANG:  unrecognized action (', varargin{2}, ')']);
	
end;



%=============================================================================
% DEFCFG  - set default configuration
%
%	returns default values for lpState

function lpState = DefCfg(idString, screen)

lpState = struct('SOURCE', idString, ...
					'FNAME', screen, ...
					'DOPLOT', 1);
				

%=============================================================================
% DOCONFIG  - config handler
%
%   returns non-empty lpState on OK, [] on cancel

function lpState = DoConfig(lpState, idString, screen)

width = 350; height = 300;
figPos = CenteredDialog(gcf, width, height);

% initialize if necessary
if isempty(lpState) || ~strcmp(lpState.SOURCE, idString),
	lpState = DefCfg(idString, screen);
end;

cfg = dialog('Name', idString, ...
	'menubar', 'none', ...
	'Position', figPos, ...
	'KeyPressFcn', 'set(gcbf,''UserData'',1);uiresume', ...
	'UserData', 0);

% about
blurb = ['This procedure tracks mouse movement while down and upon release sets a label, ', ...
	'either at the release point (shift-click), or at the nearest velocity minimum relative ', ...
	'to the release point (ctl-click).  If two labels are set on the same trajectory representing ', ...
	'an interval of cyclic behavior (e.g. jaw lowering/raising) then additional labels placed ', ...
	'between them, potentially on other trajectories, are characterized on export in terms of ', ...
	'their phase angle relative to the displacement/velocity cycle determined by the bracketing ', ...
	'labels.  Ctl-click and drag on existing labels to snap to a new velocity minimum, or ', ...
	'shift-click and drag for hand placement.'];

uicontrol(cfg, ...
	'Style', 'frame', ...
	'Position', [10 height-160 width-20 150]);
uicontrol(cfg, ...
	'Style', 'text', ...
	'HorizontalAlignment', 'left', ...
	'String', blurb, ...
	'Position', [13 height-155 width-26 140]);

% label filename
h = 5.5;
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
h = h - 2.7;
cb = uicontrol(cfg, ...
	'Style', 'checkbox', ...
	'HorizontalAlignment', 'left', ...
	'String', 'Make phase plots on Export', ...
	'Units', 'characters', ...
	'value', lpState.DOPLOT, ...
	'Position', [13 h+.7 50 2]);

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
		if isempty(e), e = '.tsv'; end;
		fName = fullfile(p,[f,e]);
	end;
	lpState.FNAME = fName;
	lpState.DOPLOT = get(cb,'value');
else,
	lpState = [];
end;
if ishandle(cfg), delete(cfg); end;


%=============================================================================
% GETSIGNAL  - get signal and its velocity based on CLICKINFO
%
% velocity is signed for monodimensional signals, else tangential (not returned for sr>2000)
%
% CLICKINFO:  [traj idx, panel idx, mod, comp (XYZ)]
%   mod is mvt, vel, acc for multidimensional trajectories; 
%   Signal, Spectrogram, F0, RMS, ZC, Vel, Abs Vel for monodimensional trajectories

function [s,v,sr] = GetSignal(state, clickInfo)

ti = clickInfo(1);				% trajectory index
tpi = clickInfo(2);				% panel index
sn = state.TEMPMAP{tpi};
s = state.DATA(ti).SIGNAL;		% [nSamps x X,Y,(Z) , vX,vY,(vZ),V , aX,aY,(aZ),A]
sr = state.DATA(ti).SRATE;
if length(clickInfo) > 3,		% multidimensional
	comp = clickInfo(4:end);
	switch clickInfo(3),
		case 1, 				% mvt
			ci = find(comp);
		case 2,					% vel
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
else,							% monodimensional
	if clickInfo(3) >= 6 & sr < 2000,		% velocity
		s(2:end-1) = (s(3:end) - s(1:end-2))./2;
		s(1) = s(2);
		s(end) = s(end-1);
		if clickInfo(3)>6, s = abs(s); end;
	end;
	ci = 1;
end;
if sr > 2000,
	v = [];							% don't compute velocity of high sample signals
else,
	s = s(:,ci);					% retain clicked component(s)
	v = [diff(s([1 3],:)) ; s(3:end,:) - s(1:end-2,:) ; diff(s([end-2 end],:))] ./ 20;
	if size(v,2) > 1,				% tangential velocity
		v = sqrt(sum(v.^2,2));
	end;
end;


%=============================================================================
% NORMALIZE  - scale to +/- 1 per Kelso et al. (1986)
%
%	mode = 0 scale mvt
%	     = 1 scale opening phase of vel
%	     = 2 scale closing phase of vel

function s = normalize(s, mode)

if nargin < 2, mode = 0; end;

switch mode,
	case 0, s = 2*s ./ (max(s) - min(s)) - (max(s) + min(s)) ./ (max(s) - min(s));
	case 1, s = s ./ max(abs(s(1:ceil(length(s)/2))));
	case 2, s = s ./ max(abs(s(floor(length(s)/2):end)));
end;
